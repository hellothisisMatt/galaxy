"""
Build indexes for searching the Tool Shed.
Run this script from the root folder, example:

$ python scripts/tool_shed/build_ts_whoosh_index.py -c config/tool_shed.yml

Make sure you adjust your Toolshed config to:
 * turn on searching with "toolshed_search_on"
 * specify "whoosh_index_dir" where the indexes will be placed

This script expects the Tool Shed's runtime virtualenv to be active.
"""
from __future__ import print_function

import argparse
import logging
import os
import shutil
import sys
import tempfile
from distutils.dir_util import copy_tree

from mercurial import hg, ui
from whoosh.filedb.filestore import FileStorage

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import tool_shed.webapp.model.mapping as ts_mapping
from galaxy.tool_util.loader_directory import load_tool_elements_from_path
from galaxy.util import (
    directory_hash_id,
    ExecutionTimer,
    pretty_print_time_interval,
    unicodify
)
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args
)
from tool_shed.webapp import (
    config as ts_config,
    model as ts_model
)
from tool_shed.webapp.search.repo_search import schema as repo_schema
from tool_shed.webapp.search.tool_search import schema as tool_schema
from tool_shed.webapp.util.hgweb_config import HgWebConfigManager

if sys.version_info > (3,):
    long = int

log = logging.getLogger()
log.addHandler(logging.StreamHandler(sys.stdout))


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build a disk-backed Toolshed repository index and tool index for searching.')
    populate_config_args(parser)
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        default=False,
                        help='Print extra info')
    args = parser.parse_args()
    app_properties = app_properties_from_args(args)
    config = ts_config.ToolShedAppConfiguration(**app_properties)
    args.dburi = config.database_connection
    args.hgweb_config_dir = config.hgweb_config_dir
    args.whoosh_index_dir = config.whoosh_index_dir
    args.file_path = config.file_path
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.debug('Full options:')
        for i in vars(args).items():
            log.debug('%s: %s' % i)
    return args


def build_index(whoosh_index_dir, file_path, hgweb_config_dir, dburi, **kwargs):
    """
    Build two search indexes simultaneously
    One is for repositories and the other for tools.
    """
    model = ts_mapping.init(file_path, dburi, engine_options={}, create_tables=False)
    sa_session = model.context.current

    #  Rare race condition exists here and below
    tool_index_dir = os.path.join(whoosh_index_dir, 'tools')
    if not os.path.exists(whoosh_index_dir):
        os.makedirs(whoosh_index_dir)
        os.makedirs(tool_index_dir)
        work_repo_dir = whoosh_index_dir
        work_tool_dir = tool_index_dir
    else:
        # Index exists, prevent in-place index regeneration
        work_repo_dir = tempfile.mkdtemp(prefix="tmp-whoosh-repo")
        work_tool_dir = tempfile.mkdtemp(prefix="tmp-whoosh-tool")

    repo_index_storage = FileStorage(work_repo_dir)
    tool_index_storage = FileStorage(work_tool_dir)
    repo_index = repo_index_storage.create_index(repo_schema)
    tool_index = tool_index_storage.create_index(tool_schema)
    repo_index_writer = repo_index.writer()
    tool_index_writer = tool_index.writer()
    repos_indexed = 0
    tools_indexed = 0

    execution_timer = ExecutionTimer()
    for repo in get_repos(sa_session, file_path, hgweb_config_dir, **kwargs):

        repo_index_writer.add_document(id=repo.get('id'),
                             name=unicodify(repo.get('name')),
                             description=unicodify(repo.get('description')),
                             long_description=unicodify(repo.get('long_description')),
                             homepage_url=unicodify(repo.get('homepage_url')),
                             remote_repository_url=unicodify(repo.get('remote_repository_url')),
                             repo_owner_username=unicodify(repo.get('repo_owner_username')),
                             categories=unicodify(repo.get('categories')),
                             times_downloaded=repo.get('times_downloaded'),
                             approved=repo.get('approved'),
                             last_updated=repo.get('last_updated'),
                             full_last_updated=repo.get('full_last_updated'),
                             repo_lineage=unicodify(repo.get('repo_lineage')))
        #  Tools get their own index
        for tool in repo.get('tools_list'):
            tool_index_writer.add_document(id=unicodify(tool.get('id')),
                                           name=unicodify(tool.get('name')),
                                           version=unicodify(tool.get('version')),
                                           description=unicodify(tool.get('description')),
                                           help=unicodify(tool.get('help')),
                                           repo_owner_username=unicodify(repo.get('repo_owner_username')),
                                           repo_name=unicodify(repo.get('name')),
                                           repo_id=repo.get('id'))
            tools_indexed += 1

        repos_indexed += 1

    tool_index_writer.commit()
    repo_index_writer.commit()

    log.info("Indexed repos: %s, tools: %s", repos_indexed, tools_indexed)
    log.info("Toolbox index finished %s", execution_timer)

    # Copy the built indexes if we were working in a tmp folder.
    if work_repo_dir is not whoosh_index_dir:
        shutil.rmtree(whoosh_index_dir)
        os.makedirs(whoosh_index_dir)
        os.makedirs(tool_index_dir)
        copy_tree(work_repo_dir, whoosh_index_dir)
        copy_tree(work_tool_dir, tool_index_dir)
        shutil.rmtree(work_repo_dir)


def get_repos(sa_session, file_path, hgweb_config_dir, **kwargs):
    """
    Load repos from DB and included tools from .xml configs.
    """
    hgwcm = HgWebConfigManager()
    hgwcm.hgweb_config_dir = hgweb_config_dir
    results = []
    # Do not index deleted, deprecated, or "tool_dependency_definition" type repositories.
    for repo in sa_session.query(ts_model.Repository).filter_by(deleted=False).filter_by(deprecated=False).filter(ts_model.Repository.type != 'tool_dependency_definition'):
        category_names = []
        for rca in sa_session.query(ts_model.RepositoryCategoryAssociation).filter(ts_model.RepositoryCategoryAssociation.repository_id == repo.id):
            for category in sa_session.query(ts_model.Category).filter(ts_model.Category.id == rca.category.id):
                category_names.append(category.name.lower())
        categories = (",").join(category_names)
        repo_id = repo.id
        name = repo.name
        description = repo.description
        long_description = repo.long_description
        homepage_url = repo.homepage_url
        remote_repository_url = repo.remote_repository_url

        times_downloaded = repo.times_downloaded
        if not isinstance(times_downloaded, (int, long)):
            times_downloaded = 0

        repo_owner_username = ''
        if repo.user_id is not None:
            user = sa_session.query(ts_model.User).filter(ts_model.User.id == repo.user_id).one()
            repo_owner_username = user.username.lower()

        approved = 'no'
        for review in repo.reviews:
            if review.approved == 'yes':
                approved = 'yes'
                break

        last_updated = pretty_print_time_interval(repo.update_time)
        full_last_updated = repo.update_time.strftime("%Y-%m-%d %I:%M %p")

        # Load all changesets of the repo for lineage.
        repo_path = hgwcm.get_entry(os.path.join("repos", repo.user.username, repo.name))
        hg_repo = hg.repository(ui.ui(), repo_path)
        lineage = []
        for changeset in hg_repo.changelog:
            lineage.append(str(changeset) + ":" + str(hg_repo[changeset]))
        repo_lineage = str(lineage)

        #  Parse all the tools within repo for a separate index.
        tools_list = []
        path = os.path.join(file_path, *directory_hash_id(repo.id))
        path = os.path.join(path, "repo_%d" % repo.id)
        if os.path.exists(path):
            tools_list.extend(load_one_dir(path))
            for root, dirs, files in os.walk(path):
                if '.hg' in dirs:
                    dirs.remove('.hg')
                for dirname in dirs:
                    tools_in_dir = load_one_dir(os.path.join(root, dirname))
                    tools_list.extend(tools_in_dir)

        results.append(dict(id=repo_id,
                            name=name,
                            description=description,
                            long_description=long_description,
                            homepage_url=homepage_url,
                            remote_repository_url=remote_repository_url,
                            repo_owner_username=repo_owner_username,
                            times_downloaded=times_downloaded,
                            approved=approved,
                            last_updated=last_updated,
                            full_last_updated=full_last_updated,
                            tools_list=tools_list,
                            repo_lineage=repo_lineage,
                            categories=categories))
    return results


def load_one_dir(path):
    tools_in_dir = []
    tool_elems = load_tool_elements_from_path(path, load_exception_handler=debug_handler)
    if tool_elems:
        for elem in tool_elems:
            root = elem[1].getroot()
            if root.tag == 'tool':
                tool = {}
                if root.find('help') is not None:
                    tool.update(dict(help=root.find('help').text))
                if root.find('description') is not None:
                    tool.update(dict(description=root.find('description').text))
                tool.update(dict(id=root.attrib.get('id'),
                                 name=root.attrib.get('name'),
                                 version=root.attrib.get('version')))
                tools_in_dir.append(tool)
    return tools_in_dir


def debug_handler(path, exc_info):
    """
    By default the underlying tool parsing logs warnings for each exception.
    This is very chatty hence this metod changes it to debug level.
    """
    log.debug("Failed to load tool with path %s." % path, exc_info=exc_info)


def main():
    args = parse_arguments()
    build_index(**vars(args))


if __name__ == "__main__":
    main()
