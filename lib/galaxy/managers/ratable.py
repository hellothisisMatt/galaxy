"""
Mixins for Ratable model managers and serializers.
"""

from sqlalchemy.sql.expression import func
from . import base

import logging
log = logging.getLogger( __name__ )


class RatableManagerMixin( object ):

    #: class of RatingAssociation (e.g. HistoryRatingAssociation)
    rating_assoc = None

    def rating( self, item, user ):
        """Returns the integer rating given to this item by the user."""
        rating = self.query_associated( self.rating_assoc, item ).filter_by( user=user ).first()
        if rating is not None:
            # get the value if there's a rating
            rating = rating.rating
        return rating

    def ratings( self, item, user ):
        """Returns all ratings given to this item."""
        return [ r.rating for r in item.ratings ]

    def ratings_avg( self, item ):
        """Returns the average of all ratings given to this item."""
        foreign_key = self._foreign_key( self.rating_assoc )
        return self.session().query( func.avg( self.rating_assoc.rating ) ).filter( foreign_key == item ).scalar()

    def ratings_count( self, item ):
        """Returns the average of all ratings given to this item."""
        foreign_key = self._foreign_key( self.rating_assoc )
        return self.session().query( func.count( self.rating_assoc.rating ) ).filter( foreign_key == item ).scalar()

    def rate( self, item, user, value, flush=True ):
        """Updates or creates a rating for this item and user. Returns the rating"""
        # TODO?: possible generic update_or_create
        # TODO?: update and create to RatingsManager (if not overkill)
        rating = self.rating( item, user )
        if not rating:
            rating = self.rating_assoc( item=item, user=user )
        rating.rating = value

        self.session().add( rating )
        if flush:
            self.flush()
        return rating

    # TODO?: all ratings for a user


class RatableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializers[ 'user_rating' ] = self.serialize_user_rating
        self.serializers[ 'community_rating' ] = self.serialize_community_rating

    def serialize_user_rating( self, item, key, user=None, **context ):
        """Returns the integer rating given to this item by the user."""
        if not user:
            raise base.ModelSerializingError( 'user_rating requires a user',
                model_class=self.manager().model_class, id=self.serialize_id( item, 'id' ) )
        return self.manager().rating( item, user )

    def serialize_community_rating( self, item, key, **context ):
        """
        Returns a dictionary containing:
            `average` the (float) average of all ratings of this object
            `count` the number of ratings
        """
        # ??: seems like two queries (albeit in-sql functions) would slower
        # than getting the rows and calc'ing both here with one query
        manager = self.manager()
        return {
            'average' : manager.ratings_avg( item ),
            'count'   : manager.ratings_count( item ),
        }


class RatableDeserializerMixin( object ):

    def add_deserializers( self ):
        self.deserializers[ 'user_rating' ] = self.deserialize_rating

    def deserialize_rating( self, item, key, val, user=None, **context ):
        if not user:
            raise base.ModelDeserializingError( 'user_rating requires a user',
                model_class=self.manager().model_class, id=self.serialize_id( item, 'id' ) )
        val = self.validate.int_range( key, val, 0, 5 )
        return self.manager().rate( item, user, val, flush=False )


class RatableFilterMixin( object ):

    def _ratings_avg_accessor( self, item ):
        return self.manager().ratings_avg( item )

    def _add_parsers( self ):
        """
        Adds the following filters:
            `community_rating`: filter
        """
        self.fn_filter_parsers.update({
            'community_rating': {
                'op': {
                    'eq' : lambda i, v: self._ratings_avg_accessor( i ) == v,
                    # TODO: default to greater than (currently 'eq' due to base/controller.py)
                    'ge' : lambda i, v: self._ratings_avg_accessor( i ) >= v,
                    'le' : lambda i, v: self._ratings_avg_accessor( i ) <= v,
                },
                'val' : float
            }
        })
