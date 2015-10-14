Splunk.Module.ExtendedSubmitButton = $.klass(Splunk.Module.SubmitButton, {
    initialize: function($super, container) {
        $super(container);
        var requiredSettings = this.getParam("requiredSettings");
        if(requiredSettings) {
            this.requiredSettings = requiredSettings.replace(/^\s+|\s+$/g, "").split(/\s*,\s*/);
        }
    },
    pushContextToChildren: function($super, explicitContext, force) {
        var ctx = explicitContext || this.getModifiedContext();
        if(this.requiredSettings) {
            for (var i = 0; i < this.requiredSettings.length; i++) {
                var setting = this.requiredSettings[i];
                if(!ctx.get(setting)) {
                    if(typeof window.console == 'object' && typeof window.console.warn == 'function') {
                        console.warn("Context push stopped because requried setting \"%s\" is not present", setting);
                    }
                    return false;
                }
            }
        }
        return $super(explicitContext, force);
    }
});
