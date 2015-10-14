$(function(){ try{

    var autoCompleteTables = null, autoCompleteColumns = null;

    var inputs = { database: $('#item-database select'), table: $('#item-table input'), fetchButton: $('#item-spl-ctrl_fetch_fields button') };

    var tablesLoading = {}, columnsLoading = {};

    function fetchTables(db) {
        if(tablesLoading[db]) return;
        tablesLoading[db] = true;

        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: Splunk.util.make_url("/custom/dbx/dbinfo/database_tables"),
            data: { database: db, nocache: String(new Date().getTime()) },
            success: function(data) {
                if(data && data.success) {
                    $(document).trigger("tables:loaded",{ db: db, tables: data.tables });
                } else {
                    Splunk.Messenger.System.getInstance().send("warn","warn","Error fetching database tables: " + (data && data.error || "No response from server"), "dberr");
                }
                tablesLoading[db] = false;
            }
        });
    }

    function updateTables() {
        var v = inputs.database.val();
        if(v) {
            if(autoCompleteTables) {
                if(v != autoCompleteTables.db) {
                    try { inputs.database.autocomplete("destroy"); } catch(e){ /* noop */ }
                    autoCompleteTables = null;
                }
            }
            fetchTables(v);
        } else {
            try { inputs.database.autocomplete("destroy"); } catch(e){ /* noop */ }
            autoCompleteTables = null;
        }
    }

    inputs.database.change(updateTables);

    $(document).bind("tables:loaded", function(e,data){
        if(data.db == inputs.database.val()) {
            autoCompleteTables = data;
            inputs.table.autocomplete({ source: data.tables, minLength: 0 });
        }
    });

    function fetchColumns(db,table) {
        var k = [db,table].join("/");
        if(columnsLoading[k]) return;
        columnsLoading[k] = true;

        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: Splunk.util.make_url("/custom/dbx/dbinfo/table_columns"),
            data: { database: db, table: table, nocache: String(new Date().getTime()) },
            success: function(data) {
                if(data && data.success) {
                    $(document).trigger("columns:loaded",{ db: db, table: table, columns: data.columns });
                }
                columnsLoading[k] = false;
            }
        });
    }

    function updateColumns() {
        var v = inputs.table.val(), db = inputs.database.val();
        if(v) {
            if(autoCompleteColumns) {
                if(v != autoCompleteColumns.table || db != autoCompleteColumns.db) {
                    autoCompleteTables = null;
                    inputs.fetchButton.attr('disabled','disabled');
                }
            }
            fetchColumns(db,v);
        } else {
            autoCompleteColumns = null;
            inputs.fetchButton.attr('disabled','disabled');
        }
    }

    var activeFieldInput = null, fillColumnsFor = null;

    $(document).bind("columns:loaded", function(e,data){
        if(inputs.database.val() == data.db && inputs.table.val() == data.table) {
            autoCompleteColumns = data;
            inputs.fetchButton.attr('disabled',false);
        }
    });

    inputs.table.bind({
        change: updateColumns,
        blur: updateColumns,
        selected: updateColumns,
        dblclick: function() {
            if(autoCompleteTables) inputs.table.autocomplete("search","");
        }
    });

    $('#item-fields input').live("focus", function(e){
        activeFieldInput = this;
        if(autoCompleteColumns && inputs.database.val() == autoCompleteColumns.db && inputs.table.val() == autoCompleteColumns.table) {
            $(this).autocomplete({ source: autoCompleteColumns.columns, minLength: 0 });
        }
    });
    $('#item-fields input').live("blur", function(e){
        if(activeFieldInput == this) activeFieldInput = null;
        try { $(this).autocomplete("destroy"); } catch(e){}
    });
    $('#item-fields input').live("dblclick", function(e){
        if(this == activeFieldInput && autoCompleteColumns && inputs.database.val() == autoCompleteColumns.db && inputs.table.val() == autoCompleteColumns.table) {
            $(this).autocomplete("search","");
        }
    });


    function clearFields() {
        var cur = $('#item-fields a.delete');
        for (var i = 0; i < cur.length; i++) {
            var link = cur[i];
            if($(link).is(":visible")) $(link).trigger("click");
        }
    }

    function fillColumns(db, table) {
        if(autoCompleteColumns && autoCompleteColumns.db == db && autoCompleteColumns.table == table) {
            clearFields();
            var cols = autoCompleteColumns.columns;
            for (var i = 0; i < cols.length; i++) {
                $('#item-fields .addnew').trigger('click');
            }
            var items = $('#item-fields input:visible');
            for (var i = 0; i < cols.length; i++) {
                $(items[i]).val(cols[i]);
            }
        }
    }

    inputs.fetchButton.click(function(e){
        e.preventDefault();
        fillColumns(inputs.database.val(), inputs.table.val());
    }).attr('disabled','disabled');

    updateTables();

    $('#item-database').addClass('widget');

} catch(e){ console.error("dblookups.js error: %o", e); }});

(function($,g){$.widget("ui.autocomplete",{options:{appendTo:"body",delay:300,minLength:1,position:{my:"left top",at:"left bottom",collision:"none"},source:null},_create:function(){var d=this,doc=this.element[0].ownerDocument;this.element.addClass("ui-autocomplete-input").attr("autocomplete","off").attr({role:"textbox","aria-autocomplete":"list","aria-haspopup":"true"}).bind("keydown.autocomplete",function(a){if(d.options.disabled){return}var b=$.ui.keyCode;switch(a.keyCode){case b.PAGE_UP:d._move("previousPage",a);break;case b.PAGE_DOWN:d._move("nextPage",a);break;case b.UP:d._move("previous",a);a.preventDefault();break;case b.DOWN:d._move("next",a);a.preventDefault();break;case b.ENTER:case b.NUMPAD_ENTER:if(d.menu.element.is(":visible")){a.preventDefault()}case b.TAB:if(!d.menu.active){return}d.menu.select(a);break;case b.ESCAPE:d.element.val(d.term);d.close(a);break;default:clearTimeout(d.searching);d.searching=setTimeout(function(){if(d.term!=d.element.val()){d.selectedItem=null;d.search(null,a)}},d.options.delay);break}}).bind("focus.autocomplete",function(){if(d.options.disabled){return}d.selectedItem=null;d.previous=d.element.val()}).bind("blur.autocomplete",function(a){if(d.options.disabled){return}clearTimeout(d.searching);d.closing=setTimeout(function(){d.close(a);d._change(a)},150)});this._initSource();this.response=function(){return d._response.apply(d,arguments)};this.menu=$("<ul></ul>").addClass("ui-autocomplete").appendTo($(this.options.appendTo||"body",doc)[0]).mousedown(function(b){var c=d.menu.element[0];if(b.target===c){setTimeout(function(){$(document).one('mousedown',function(a){if(a.target!==d.element[0]&&a.target!==c&&!$.ui.contains(c,a.target)){d.close()}})},1)}setTimeout(function(){clearTimeout(d.closing)},13)}).menu({focus:function(a,b){var c=b.item.data("item.autocomplete");if(false!==d._trigger("focus",null,{item:c})){if(/^key/.test(a.originalEvent.type)){d.element.val(c.value)}}},selected:function(a,b){var c=b.item.data("item.autocomplete"),previous=d.previous;if(d.element[0]!==doc.activeElement){d.element.focus();d.previous=previous}if(false!==d._trigger("select",a,{item:c})){d.term=c.value;d.element.val(c.value)}d.close(a);d.selectedItem=c},blur:function(a,b){if(d.menu.element.is(":visible")&&(d.element.val()!==d.term)){d.element.val(d.term)}}}).zIndex(this.element.zIndex()+1).css({top:0,left:0}).hide().data("menu");if($.fn.bgiframe){this.menu.element.bgiframe()}},destroy:function(){this.element.removeClass("ui-autocomplete-input").removeAttr("autocomplete").removeAttr("role").removeAttr("aria-autocomplete").removeAttr("aria-haspopup");this.menu.element.remove();$.Widget.prototype.destroy.call(this)},_setOption:function(a,b){$.Widget.prototype._setOption.apply(this,arguments);if(a==="source"){this._initSource()}if(a==="appendTo"){this.menu.element.appendTo($(b||"body",this.element[0].ownerDocument)[0])}},_initSource:function(){var f=this,array,url;if($.isArray(this.options.source)){array=this.options.source;this.source=function(a,b){b($.ui.autocomplete.filter(array,a.term))}}else if(typeof this.options.source==="string"){url=this.options.source;this.source=function(d,e){if(f.xhr){f.xhr.abort()}f.xhr=$.getJSON(url,d,function(a,b,c){if(c===f.xhr){e(a)}f.xhr=null})}}else{this.source=this.options.source}},search:function(a,b){a=a!=null?a:this.element.val();this.term=this.element.val();if(a.length<this.options.minLength){return this.close(b)}clearTimeout(this.closing);if(this._trigger("search")===false){return}return this._search(a)},_search:function(a){this.element.addClass("ui-autocomplete-loading");this.source({term:a},this.response)},_response:function(a){if(a.length){a=this._normalize(a);this._suggest(a);this._trigger("open")}else{this.close()}this.element.removeClass("ui-autocomplete-loading")},close:function(a){clearTimeout(this.closing);if(this.menu.element.is(":visible")){this._trigger("close",a);this.menu.element.hide();this.menu.deactivate()}},_change:function(a){if(this.previous!==this.element.val()){this._trigger("change",a,{item:this.selectedItem})}},_normalize:function(b){if(b.length&&b[0].label&&b[0].value){return b}return $.map(b,function(a){if(typeof a==="string"){return{label:a,value:a}}return $.extend({label:a.label||a.value,value:a.value||a.label},a)})},_suggest:function(a){var b=this.menu.element.empty().zIndex(this.element.zIndex()+1),menuWidth,textWidth;this._renderMenu(b,a);this.menu.deactivate();this.menu.refresh();this.menu.element.show().position($.extend({of:this.element},this.options.position));menuWidth=b.width("").outerWidth();textWidth=this.element.outerWidth();b.outerWidth(Math.max(menuWidth,textWidth))},_renderMenu:function(c,d){var e=this;$.each(d,function(a,b){e._renderItem(c,b)})},_renderItem:function(a,b){return $("<li></li>").data("item.autocomplete",b).append($("<a></a>").text(b.label)).appendTo(a)},_move:function(a,b){if(!this.menu.element.is(":visible")){this.search(null,b);return}if(this.menu.first()&&/^previous/.test(a)||this.menu.last()&&/^next/.test(a)){this.element.val(this.term);this.menu.deactivate();return}this.menu[a](b)},widget:function(){return this.menu.element}});$.extend($.ui.autocomplete,{escapeRegex:function(a){return a.replace(/[-[\]{}()*+?.,\\^$|#\s]/g,"\\$&")},filter:function(b,c){var d=new RegExp($.ui.autocomplete.escapeRegex(c),"i");return $.grep(b,function(a){return d.test(a.label||a.value||a)})}})}(jQuery));(function($){$.widget("ui.menu",{_create:function(){var b=this;this.element.addClass("ui-menu ui-widget ui-widget-content ui-corner-all").attr({role:"listbox","aria-activedescendant":"ui-active-menuitem"}).click(function(a){if(!$(a.target).closest(".ui-menu-item a").length){return}a.preventDefault();b.select(a)});this.refresh()},refresh:function(){var b=this;var c=this.element.children("li:not(.ui-menu-item):has(a)").addClass("ui-menu-item").attr("role","menuitem");c.children("a").addClass("ui-corner-all").attr("tabindex",-1).mouseenter(function(a){b.activate(a,$(this).parent())}).mouseleave(function(){b.deactivate()})},activate:function(a,b){this.deactivate();if(this.hasScroll()){var c=b.offset().top-this.element.offset().top,scroll=this.element.attr("scrollTop"),elementHeight=this.element.height();if(c<0){this.element.attr("scrollTop",scroll+c)}else if(c>=elementHeight){this.element.attr("scrollTop",scroll+c-elementHeight+b.height())}}this.active=b.eq(0).children("a").addClass("ui-state-hover").attr("id","ui-active-menuitem").end();this._trigger("focus",a,{item:b})},deactivate:function(){if(!this.active){return}this.active.children("a").removeClass("ui-state-hover").removeAttr("id");this._trigger("blur");this.active=null},next:function(a){this.move("next",".ui-menu-item:first",a)},previous:function(a){this.move("prev",".ui-menu-item:last",a)},first:function(){return this.active&&!this.active.prevAll(".ui-menu-item").length},last:function(){return this.active&&!this.active.nextAll(".ui-menu-item").length},move:function(a,b,c){if(!this.active){this.activate(c,this.element.children(b));return}var d=this.active[a+"All"](".ui-menu-item").eq(0);if(d.length){this.activate(c,d)}else{this.activate(c,this.element.children(b))}},nextPage:function(b){if(this.hasScroll()){if(!this.active||this.last()){this.activate(b,this.element.children(":first"));return}var c=this.active.offset().top,height=this.element.height(),result=this.element.children("li").filter(function(){var a=$(this).offset().top-c-height+$(this).height();return a<10&&a>-10});if(!result.length){result=this.element.children(":last")}this.activate(b,result)}else{this.activate(b,this.element.children(!this.active||this.last()?":first":":last"))}},previousPage:function(b){if(this.hasScroll()){if(!this.active||this.first()){this.activate(b,this.element.children(":last"));return}var c=this.active.offset().top,height=this.element.height();result=this.element.children("li").filter(function(){var a=$(this).offset().top-c+height-$(this).height();return a<10&&a>-10});if(!result.length){result=this.element.children(":first")}this.activate(b,result)}else{this.activate(b,this.element.children(!this.active||this.first()?":last":":first"))}},hasScroll:function(){return this.element.height()<this.element.attr("scrollHeight")},select:function(a){this._trigger("selected",a,{item:this.active})}})}(jQuery));