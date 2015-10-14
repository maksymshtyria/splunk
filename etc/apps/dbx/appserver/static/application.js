if(Splunk.util.getCurrentView() == 'dbinfo') {
    $.extend(Splunk.Module.EntitySelectLister.prototype, {
        renderResults: function(html) {
            $('select', this.container).empty();
            $('select', this.container).append('<option value="" selected>Select a database</option>');
            $('select', this.container).append(html);
            this.selectSelected();
            $('select', this.container).removeAttr('disabled');
            Splunk.Module.AbstractEntityLister.prototype.renderResults.call(this, html);
        }
    });
    Splunk.Module.ConvertToIntention = $.klass(Splunk.Module.ConvertToIntention, {
        isReadyForContextPush: function($super) {
            var ctx = this.getContext();
            for (var i=0; i<this._matches.length; i++) {
                if(!ctx.get(this._matches[i])) return false;
            }
            return $super();
        }
    });
    Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
        renderResults: function($super,data) {
            $super(data);
            $('td[field=ref]', this.container).hide();
            $('span.sortLabel:contains("ref")', this.container).parents('th').hide();
        }
    });
    Splunk.Module.TextSetting = $.klass(Splunk.Module.TextSetting, {
        _bindEventOnFormElement: function($super){ $super('keydown'); this._formElement.val("*"); },
        onEvent: function(e) {
            if(e.keyCode == 13) {
                this.pushContextToChildren();
            }
        }
    });
    Splunk.Module.SearchSelectLister = $.klass(Splunk.Module.SearchSelectLister,{
        getResults: function($super) {
            $(this.container).find('select>option').text('Loading...');
            $super();
        },
        selectSelected: function(){
            $('select > option:contains("(default)")', this.container).prop('selected', true);
        }
    });
}
if(Splunk.util.getCurrentView() == 'dbquery') {
    Splunk.Module.JobStatus = $.klass(Splunk.Module.JobStatus, {
        getHeaderFragment: function(name, job) {
            var returnDict = {"name": name};
            switch (name) {
                case "events":
                    var events = job.getResultCount();
                    if (job.isDone()) {
                        returnDict["text"] = sprintf(ungettext('%s rows returned', '%s rows returned', events), format_number(events));
                    } else {
                        returnDict["text"] = sprintf(/* TRANS: &#8805 is the greater than or equal to symbol */ungettext('&#8805; %s matching rows', '&#8805; %s matching rows', events), format_number(events));
                    }
                    break;
                case "scanned":
                    var scanned = job.getScanCount();
                    returnDict["text"] = sprintf(ungettext('%s scanned rows', '%s scanned rows', scanned), format_number(scanned));
                    break;
                case "progress":
                    var progress = Math.round(job.getDoneProgress() * 100);
                    returnDict["text"] = sprintf(_('%s%% complete'), progress);
                    break;
                case "results":
                    var results = job.getResultCount();
                    returnDict["text"] = sprintf(ungettext('%s result', '%s results', results), format_number(results));
                    break;
                default:
                    this.logger.error("getHeaderFragment - unknown name provided - ", name);
                    returnDict["text"] = "";
                    break;
            }
            return returnDict;
        }
    });
}
