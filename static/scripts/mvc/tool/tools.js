define("mvc/tool/tools",["exports","libs/underscore","viz/trackster/util","mvc/dataset/data","mvc/tool/tool-form"],function(e,t,i,n,o){"use strict";function s(e){return e&&e.__esModule?e:{default:e}}Object.defineProperty(e,"__esModule",{value:!0});var l=function(e){if(e&&e.__esModule)return e;var t={};if(null!=e)for(var i in e)Object.prototype.hasOwnProperty.call(e,i)&&(t[i]=e[i]);return t.default=e,t}(t),a=s(i),r=s(n),c=(s(o),{hidden:!1,show:function(){this.set("hidden",!1)},hide:function(){this.set("hidden",!0)},toggle:function(){this.set("hidden",!this.get("hidden"))},is_visible:function(){return!this.attributes.hidden}}),u=Backbone.Model.extend({defaults:{name:null,label:null,type:null,value:null,html:null,num_samples:5},initialize:function(e){this.attributes.html=unescape(this.attributes.html)},copy:function(){return new u(this.toJSON())},set_value:function(e){this.set("value",e||"")}}),h=Backbone.Collection.extend({model:u}),d=u.extend({}),p=u.extend({set_value:function(e){this.set("value",parseInt(e,10))},get_samples:function(){return d3.scale.linear().domain([this.get("min"),this.get("max")]).ticks(this.get("num_samples"))}}),f=p.extend({set_value:function(e){this.set("value",parseFloat(e))}}),_=u.extend({get_samples:function(){return l.map(this.get("options"),function(e){return e[0]})}});u.subModelTypes={integer:p,float:f,data:d,select:_};var m=Backbone.Model.extend({defaults:{id:null,name:null,description:null,target:null,inputs:[],outputs:[]},urlRoot:Galaxy.root+"api/tools",initialize:function(e){this.set("inputs",new h(l.map(e.inputs,function(e){return new(u.subModelTypes[e.type]||u)(e)})))},toJSON:function(){var e=Backbone.Model.prototype.toJSON.call(this);return e.inputs=this.get("inputs").map(function(e){return e.toJSON()}),e},remove_inputs:function(e){var t=this,i=t.get("inputs").filter(function(t){return-1!==e.indexOf(t.get("type"))});t.get("inputs").remove(i)},copy:function(e){var t=new m(this.toJSON());if(e){var i=new Backbone.Collection;t.get("inputs").each(function(e){e.get_samples()&&i.push(e)}),t.set("inputs",i)}return t},apply_search_results:function(e){return-1!==l.indexOf(e,this.attributes.id)?this.show():this.hide(),this.is_visible()},set_input_value:function(e,t){this.get("inputs").find(function(t){return t.get("name")===e}).set("value",t)},set_input_values:function(e){var t=this;l.each(l.keys(e),function(i){t.set_input_value(i,e[i])})},run:function(){return this._run()},rerun:function(e,t){return this._run({action:"rerun",target_dataset_id:e.id,regions:t})},get_inputs_dict:function(){var e={};return this.get("inputs").each(function(t){e[t.get("name")]=t.get("value")}),e},_run:function(e){var t=l.extend({tool_id:this.id,inputs:this.get_inputs_dict()},e),i=$.Deferred(),n=new a.default.ServerStateDeferred({ajax_settings:{url:this.urlRoot,data:JSON.stringify(t),dataType:"json",contentType:"application/json",type:"POST"},interval:2e3,success_fn:function(e){return"pending"!==e}});return $.when(n.go()).then(function(e){i.resolve(new r.default.DatasetCollection(e))}),i}});l.extend(m.prototype,c);Backbone.View.extend({});var v=Backbone.Collection.extend({model:m}),g=Backbone.Model.extend(c),b=Backbone.Model.extend({defaults:{elems:[],open:!1},clear_search_results:function(){l.each(this.attributes.elems,function(e){e.show()}),this.show(),this.set("open",!1)},apply_search_results:function(e){var t,i=!0;l.each(this.attributes.elems,function(n){n instanceof g?(t=n).hide():n instanceof m&&n.apply_search_results(e)&&(i=!1,t&&t.show())}),i?this.hide():(this.show(),this.set("open",!0))}});l.extend(b.prototype,c);var y=Backbone.Model.extend({defaults:{search_hint_string:"search tools",min_chars_for_search:3,clear_btn_url:"",visible:!0,query:"",results:null,clear_key:27},urlRoot:Galaxy.root+"api/tools",initialize:function(){this.on("change:query",this.do_search)},do_search:function(){var e=this.attributes.query;if(e.length<this.attributes.min_chars_for_search)this.set("results",null);else{var t=e;this.timer&&clearTimeout(this.timer),$("#search-clear-btn").hide(),$("#search-spinner").show();var i=this;this.timer=setTimeout(function(){"undefined"!=typeof ga&&ga("send","pageview",Galaxy.root+"?q="+t),$.get(i.urlRoot,{q:t},function(e){i.set("results",e),$("#search-spinner").hide(),$("#search-clear-btn").show()},"json")},400)}},clear_search:function(){this.set("query",""),this.set("results",null)}});l.extend(y.prototype,c);var w=Backbone.Model.extend({initialize:function(e){this.attributes.tool_search=e.tool_search,this.attributes.tool_search.on("change:results",this.apply_search_results,this),this.attributes.tools=e.tools,this.attributes.layout=new Backbone.Collection(this.parse(e.layout))},parse:function(e){var t=this;return l.map(e,function e(i){var n=i.model_class;if(n.indexOf("Tool")===n.length-4)return t.attributes.tools.get(i.id);if("ToolSection"===n){var o=l.map(i.elems,e);return i.elems=o,new b(i)}return"ToolSectionLabel"===n?new g(i):void 0})},clear_search_results:function(){this.get("layout").each(function(e){e instanceof b?e.clear_search_results():e.show()})},apply_search_results:function(){var e=this.get("tool_search").get("results");if(null!==e){var t=null;this.get("layout").each(function(i){i instanceof g?(t=i).hide():i instanceof m?i.apply_search_results(e)&&t&&t.show():(t=null,i.apply_search_results(e))})}else this.clear_search_results()}}),x=Backbone.View.extend({initialize:function(){this.model.on("change:hidden",this.update_visible,this),this.update_visible()},update_visible:function(){this.model.attributes.hidden?this.$el.hide():this.$el.show()}}),k=x.extend({tagName:"div",render:function(){var e=$("<div/>");e.append(M.tool_link(this.model.toJSON()));var t=this.model.get("form_style",null);if("upload1"===this.model.id)e.find("a").on("click",function(e){e.preventDefault(),Galaxy.upload.show()});else if("regular"===t){var i=this;e.find("a").on("click",function(e){e.preventDefault(),Galaxy.router.push("/",{tool_id:i.model.id,version:i.model.get("version")})})}return this.$el.append(e),this}}),S=x.extend({tagName:"div",className:"toolPanelLabel",render:function(){return this.$el.append($("<span/>").text(this.model.attributes.text)),this}}),B=x.extend({tagName:"div",className:"toolSectionWrapper",initialize:function(){x.prototype.initialize.call(this),this.model.on("change:open",this.update_open,this)},render:function(){this.$el.append(M.panel_section(this.model.toJSON()));var e=this.$el.find(".toolSectionBody");return l.each(this.model.attributes.elems,function(t){if(t instanceof m){var i=new k({model:t,className:"toolTitle"});i.render(),e.append(i.$el)}else if(t instanceof g){var n=new S({model:t});n.render(),e.append(n.$el)}}),this},events:{"click .toolSectionTitle > a":"toggle"},toggle:function(){this.model.set("open",!this.model.attributes.open)},update_open:function(){this.model.attributes.open?this.$el.children(".toolSectionBody").slideDown("fast"):this.$el.children(".toolSectionBody").slideUp("fast")}}),N=Backbone.View.extend({tagName:"div",id:"tool-search",className:"bar",events:{click:"focus_and_select","keyup :input":"query_changed","change :input":"query_changed","click #search-clear-btn":"clear"},render:function(){return this.$el.append(M.tool_search(this.model.toJSON())),this.model.is_visible()||this.$el.hide(),$("#messagebox").is(":visible")&&this.$el.css("top","95px"),this.$el.find("[title]").tooltip(),this},focus_and_select:function(){this.$el.find(":input").focus().select()},clear:function(){return this.model.clear_search(),this.$el.find(":input").val(""),this.focus_and_select(),!1},query_changed:function(e){if(this.model.attributes.clear_key&&this.model.attributes.clear_key===e.which)return this.clear(),!1;this.model.set("query",this.$el.find(":input").val())}}),T=Backbone.View.extend({tagName:"div",className:"toolMenu",initialize:function(){this.model.get("tool_search").on("change:results",this.handle_search_results,this)},render:function(){var e=this,t=new N({model:this.model.get("tool_search")});return t.render(),e.$el.append(t.$el),this.model.get("layout").each(function(t){if(t instanceof b){var i=new B({model:t});i.render(),e.$el.append(i.$el)}else if(t instanceof m){var n=new k({model:t,className:"toolTitleNoSection"});n.render(),e.$el.append(n.$el)}else if(t instanceof g){var o=new S({model:t});o.render(),e.$el.append(o.$el)}}),e.$el.find("a.tool-link").click(function(t){var i=$(this).attr("class").split(/\s+/)[0],n=e.model.get("tools").get(i);e.trigger("tool_link_click",t,n)}),this},handle_search_results:function(){var e=this.model.get("tool_search").get("results");e&&0===e.length?$("#search-no-results").show():$("#search-no-results").hide()}}),O=Backbone.View.extend({className:"toolForm",render:function(){this.$el.children().remove(),this.$el.append(M.tool_form(this.model.toJSON()))}}),M=(Backbone.View.extend({className:"toolMenuAndView",initialize:function(){this.tool_panel_view=new T({collection:this.collection}),this.tool_form_view=new O},render:function(){this.tool_panel_view.render(),this.tool_panel_view.$el.css("float","left"),this.$el.append(this.tool_panel_view.$el),this.tool_form_view.$el.hide(),this.$el.append(this.tool_form_view.$el);var e=this;this.tool_panel_view.on("tool_link_click",function(t,i){t.preventDefault(),e.show_tool(i)})},show_tool:function(e){var t=this;e.fetch().done(function(){t.tool_form_view.model=e,t.tool_form_view.render(),t.tool_form_view.$el.show(),$("#left").width("650px")})}}),{tool_search:l.template(['<input id="tool-search-query" class="search-query parent-width" name="query" ','placeholder="<%- search_hint_string %>" autocomplete="off" type="text" />','<a id="search-clear-btn" title="clear search (esc)"> </a>','<span id="search-spinner" class="search-spinner fa fa-spinner fa-spin"></span>'].join("")),panel_section:l.template(['<div class="toolSectionTitle" id="title_<%- id %>">','<a href="javascript:void(0)"><span><%- name %></span></a>',"</div>",'<div id="<%- id %>" class="toolSectionBody" style="display: none;">','<div class="toolSectionBg"></div>',"<div>"].join("")),tool_link:l.template(['<a class="<%- id %> tool-link" href="<%= link %>" target="<%- target %>" minsizehint="<%- min_width %>">','<span class="labels">',"<% _.each( labels, function( label ){ %>",'<span class="label label-default label-<%- label %>">',"<%- label %>","</span>","<% }); %>","</span>",'<span class="tool-old-link">',"<%- name %>","</span>"," <%- description %>","</a>"].join("")),tool_form:l.template(['<div class="toolFormTitle"><%- tool.name %> (version <%- tool.version %>)</div>','<div class="toolFormBody">',"<% _.each( tool.inputs, function( input ){ %>",'<div class="form-row">','<label for="<%- input.name %>"><%- input.label %>:</label>','<div class="form-row-input">',"<%= input.html %>","</div>",'<div class="toolParamHelp" style="clear: both;">',"<%- input.help %>","</div>",'<div style="clear: both;"></div>',"</div>","<% }); %>","</div>",'<div class="form-row form-actions">','<input type="submit" class="btn btn-primary" name="runtool_btn" value="Execute" />',"</div>",'<div class="toolHelp">','<div class="toolHelpBody"><% tool.help %></div>',"</div>"].join(""),{variable:"tool"})});e.default={ToolParameter:u,IntegerToolParameter:p,SelectToolParameter:_,Tool:m,ToolCollection:v,ToolSearch:y,ToolPanel:w,ToolPanelView:T,ToolFormView:O}});