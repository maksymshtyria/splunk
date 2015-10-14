Splunk.Module.DBXSQLQuery = $.klass(Splunk.Module, {
    initialize:function ($super, ct) {
        $super(ct);
        this.debug = false;
        this.childEnforcement = Splunk.Module.ALWAYS_REQUIRE;
        this.loadDatabases();
        $(ct).find('.searchButton').click(this.executeSearch.bind(this));
        $(ct).find('.syntax-switch').click(this.switchSyntax.bind(this));
        if(Splunk.util.normalizeBoolean(this.getParam("syntaxHighlighting")) === true) {
            this.switchSyntax();
        }
    },
    switchSyntax: function() {
        if(this.cm) {
            this.cm.toTextArea();
            this.cm = null;
            $(this.container).find(".syntax-switch a").text("Enable syntax highlighting");
            this.setParam("syntaxHighlighting","false");
        } else {
            this.loadCodeMirror();
        }
    },
    loadCodeMirror: function() {
        if(window.CodeMirror) {
            this.enableSytaxHighlighter();
        } else if(!this._cmLoading) {
            this._cmLoading = true;
            $('<link rel="stylesheet" type="text/css">').attr({ href: Splunk.util.make_url('/static/css/codemirror.css') }).appendTo($('head'));
            $.getScript(Splunk.util.make_url('/static/js/contrib/codemirror.js'), this.enableSytaxHighlighter.bind(this));
        }
    },
    enableSytaxHighlighter: function() {
        if(this.debug) console.log('enabling syntax highlighter');
        if(!this._sqlModeLoaded) {
            loadSQLMode();
            this._sqlModeLoaded = true;
        }
        var execSQL = this.executeSearch.bind(this);
        this.cm = CodeMirror.fromTextArea($(this.container).find('textarea').get(0), {
            mode: { name: "sql", htmlMode: false },
            lineNumbers: true,
            lineWrapping: true,
            onKeyEvent: function(cm, e) {
                var evt = $.event.fix(e);
                if(evt.keyCode == 13 && evt.metaKey) {
                    e.stop();
                    setTimeout(execSQL,1);
                    return true;
                }
            }
        });
        $(this.container).find(".syntax-switch a").text("Disable syntax highlighting");
        this.setParam("syntaxHighlighting","true");
    },
    disableSyntaxHighlighter: function() {

    },
    executeSearch: function() {
        if(! this.getSelectedDatabase()) {
            Splunk.Messenger.System.getInstance().send('warn','dbx','No database selected');
            return;
        }
        if(! this.getSQLQuery()) {
            Splunk.Messenger.System.getInstance().send('warn','dbx','No SQL statement specified');
            return;
        }
        this.pushContextToChildren(null, true);
    },
    loadDatabases:function () {
        $.getJSON(Splunk.util.make_url('api/lists/entities/dbx/databases'), { output_mode:'json', count:0, search:'disabled!=1', nocache: String(new Date().getTime()) }, this.renderDatabases.bind(this));
    },
    renderDatabases:function (databases) {
        var select = $(this.container).find('#database-input');
        select.html('');
        if (!databases.length) {
            $('<option/>').text('No database configured').appendTo(select);
            select.attr({ disabled:'disabled' });
        } else {
            $('<option/>').attr({ value:'', selected:'selected' }).text('Select a database...').appendTo(select);
            for (var i = 0; i < databases.length; i++) {
                $('<option/>').attr('value', databases[i].name).text(databases[i].name).appendTo(select);
            }
        }
        if(this._selectedDB) select.val(this._selectedDB);
        this._dbLoaded = true;
        if(this.debug) console.log(databases);
    },
    getSelectedDatabase: function() {
        if(this._dbLoaded) return $(this.container).find('#database-input').val();
        else return this._selectedDB;
    },
    createSearchString:function () {
        var db = this.getSelectedDatabase();
        if (/[^\w]/.test(db)) {
            db = sprintf('"%s"', db.replace(/"/g, '\\"'));
        }
        var query = $.trim(this.getSQLQuery()).replace(/\r/g, '\\r').replace(/\n/g, '\\n').replace(/"/g, '\\"');
        var limit = $(this.container).find('#limit-input').is(":checked") ? 'limit=1000' : '';
        var search = sprintf('| dbquery %s %s "%s"', db, limit, query);
        if(this.debug) console.log('search: %o', search);
        return search;
    },
    getSQLQuery: function() {
        if(this.cm) return this.cm.getValue();
        else return $(this.container).find('textarea').val();
    },
    applyContext: function($super,context) {
        if(this.debug) console.log('applyContext(%o)', context);

        var search = context.get('search');

        if(search) {
            var baseSearch = search.getBaseSearch();
            if(baseSearch) {
                var m = baseSearch.match(/^\s*\|\s*dbquery\s+("[^"]+"|\S+)\s+(?:limit=\d+\s+)?"(.+)"\s*$/);
                if(m) {
                    if(this.debug) console.log('base search db=%o sql=%o', m[1],m[2]);
                    if(this._dbLoaded) $(this.container).find('#database-input').val(m[1]);
                    else this._selectedDB = m[1];
                    var query = m[2];
                    query = eval("'" + query.replace(/'/,"\\'") + "'");
                    if(this.cm) this.cm.setValue(query);
                    else $(this.container).find('textarea').val(query);
                } else {
                    if(this.debug) console.error('didnt match');
                }
            }
        }
        $super(context);

        if(this.checkRequiredSettings()) {
            this.pushContextToChildren(null, true);
        }
    },
    getModifiedContext:function (ctx) {
        if(this.debug) console.log('getModifiedContext(%o)',ctx);
        if(!ctx) {
            ctx = this.getContext();
            var search = ctx.get('search');
            search.abandonJob();
            if (this.isReadyForContextPush()) {
                search.setBaseSearch(this.createSearchString());
                ctx.set('search', search);
            }
        }
        return ctx;
    },
    checkRequiredSettings: function() {
        if(! this.getSelectedDatabase()) return false;
        if(! this.getSQLQuery()) return false;
        if(this.debug) console.log('required check passed');
        return true;
    },
    isReadyForContextPush:function ($super) {
        if(this.debug) console.log('isReadyForContextPush');
        if(!this.checkRequiredSettings()) return Splunk.Module.CANCEL;
        return $super();
    },
    pushContextToChildren:function ($super, explicitContext, force) {
        if(this.debug) console.log('pushContextToChildren(%o)', explicitContext);
        return $super(this.getModifiedContext(explicitContext), force);
    },
    onContextChange: function() {
        if(this.debug) console.log('onContextChange()');
    },
    resetUI: function() {}
});

function loadSQLMode(){

    CodeMirror.defineMode("sql", function(config) {
      var indentUnit = config.indentUnit;
      var curPunc;

      function wordRegexp(words) {
        return new RegExp("^(?:" + words.join("|") + ")$", "i");
      }
      var ops = wordRegexp(["str", "lang", "langmatches", "datatype", "bound", "sameterm", "isiri", "isuri",
                            "isblank", "isliteral", "union", "a"]);
      var keywords = wordRegexp([
          "alter", "grant", "revoke", "primary", "key", "table", "start",
              "transaction", "select", "update", "insert", "delete", "create", "describe",
              "from", "into", "values", "where", "join", "inner", "left", "natural", "and",
              "or", "in", "not", "xor", "like", "using", "on", "order", "group", "by",
              "asc", "desc", "limit", "offset", "union", "all", "as", "distinct", "set",
              "commit", "rollback", "replace", "view", "database", "separator", "if",
              "exists", "null", "truncate", "status", "show", "lock", "unique","having",
          "bigint", "binary", "bit", "blob", "bool", "char", "character", "date",
             "datetime", "dec", "decimal", "double", "enum", "float", "float4", "float8",
             "int", "int1", "int2", "int3", "int4", "int8", "integer", "long", "longblob",
             "longtext", "mediumblob", "mediumint", "mediumtext", "middleint", "nchar",
             "numeric", "real", "set", "smallint", "text", "time", "timestamp", "tinyblob",
             "tinyint", "tinytext", "varbinary", "varchar", "year",
          "abs", "acos", "adddate", "aes_encrypt", "aes_decrypt", "ascii",
              "asin", "atan", "atan2", "avg", "benchmark", "bin", "bit_and",
              "bit_count", "bit_length", "bit_or", "cast", "ceil", "ceiling",
              "char_length", "character_length", "coalesce", "concat", "concat_ws",
              "connection_id", "conv", "convert", "cos", "cot", "count", "curdate",
              "current_date", "current_time", "current_timestamp", "current_user",
              "curtime", "database", "date_add", "date_format", "date_sub",
              "dayname", "dayofmonth", "dayofweek", "dayofyear", "decode", "degrees",
              "des_encrypt", "des_decrypt", "elt", "encode", "encrypt", "exp",
              "export_set", "extract", "field", "find_in_set", "floor", "format",
              "found_rows", "from_days", "from_unixtime", "get_lock", "greatest",
              "group_unique_users", "hex", "ifnull", "inet_aton", "inet_ntoa", "instr",
              "interval", "is_free_lock", "isnull", "last_insert_id", "lcase", "least",
              "left", "length", "ln", "load_file", "locate", "log", "log2", "log10",
              "lower", "lpad", "ltrim", "make_set", "master_pos_wait", "max", "md5",
              "mid", "min", "mod", "monthname", "now", "nullif", "oct", "octet_length",
              "ord", "password", "period_add", "period_diff", "pi", "position",
              "pow", "power", "quarter", "quote", "radians", "rand", "release_lock",
              "repeat", "reverse", "right", "round", "rpad", "rtrim", "sec_to_time",
              "session_user", "sha", "sha1", "sign", "sin", "soundex", "space", "sqrt",
              "std", "stddev", "strcmp", "subdate", "substring", "substring_index",
              "sum", "sysdate", "system_user", "tan", "time_format", "time_to_sec",
              "to_days", "trim", "ucase", "unique_users", "unix_timestamp", "upper",
              "user", "version", "week", "weekday", "yearweek"
      ]);
      var operatorChars = /[*+\-<>=&|]/;

      function tokenBase(stream, state) {
        var ch = stream.next();
        curPunc = null;
        if (ch == "$" || ch == "?") {
          stream.match(/^[\w\d]*/);
          return "variable-2";
        }
        else if (ch == "<" && !stream.match(/^[\s\u00a0=]/, false)) {
          stream.match(/^[^\s\u00a0>]*>?/);
          return "atom";
        }
        else if (ch == "\"" || ch == "'") {
          state.tokenize = tokenLiteral(ch);
          return state.tokenize(stream, state);
        }
        else if (ch == "`") {
          state.tokenize = tokenOpLiteral(ch);
          return state.tokenize(stream, state);
        }
        else if (/[{}\(\),\.;\[\]]/.test(ch)) {
          curPunc = ch;
          return null;
        }
        else if (ch == "-") {
          var ch2 = stream.next();
          if (ch2=="-") {
          	stream.skipToEnd();
          	return "comment";
          }
        }
        else if (operatorChars.test(ch)) {
          stream.eatWhile(operatorChars);
          return null;
        }
        else if (ch == ":") {
          stream.eatWhile(/[\w\d\._\-]/);
          return "atom";
        }
        else {
          stream.eatWhile(/[_\w\d]/);
          if (stream.eat(":")) {
            stream.eatWhile(/[\w\d_\-]/);
            return "atom";
          }
          var word = stream.current(), type;
          if (ops.test(word))
            return null;
          else if (keywords.test(word))
            return "keyword";
          else
            return "variable";
        }
      }

      function tokenLiteral(quote) {
        return function(stream, state) {
          var escaped = false, ch;
          while ((ch = stream.next()) != null) {
            if (ch == quote && !escaped) {
              state.tokenize = tokenBase;
              break;
            }
            escaped = !escaped && ch == "\\";
          }
          return "string";
        };
      }

      function tokenOpLiteral(quote) {
        return function(stream, state) {
          var escaped = false, ch;
          while ((ch = stream.next()) != null) {
            if (ch == quote && !escaped) {
              state.tokenize = tokenBase;
              break;
            }
            escaped = !escaped && ch == "\\";
          }
          return "variable-2";
        };
      }


      function pushContext(state, type, col) {
        state.context = {prev: state.context, indent: state.indent, col: col, type: type};
      }
      function popContext(state) {
        state.indent = state.context.indent;
        state.context = state.context.prev;
      }

      return {
        startState: function(base) {
          return {tokenize: tokenBase,
                  context: null,
                  indent: 0,
                  col: 0};
        },

        token: function(stream, state) {
          if (stream.sol()) {
            if (state.context && state.context.align == null) state.context.align = false;
            state.indent = stream.indentation();
          }
          if (stream.eatSpace()) return null;
          var style = state.tokenize(stream, state);

          if (style != "comment" && state.context && state.context.align == null && state.context.type != "pattern") {
            state.context.align = true;
          }

          if (curPunc == "(") pushContext(state, ")", stream.column());
          else if (curPunc == "[") pushContext(state, "]", stream.column());
          else if (curPunc == "{") pushContext(state, "}", stream.column());
          else if (/[\]\}\)]/.test(curPunc)) {
            while (state.context && state.context.type == "pattern") popContext(state);
            if (state.context && curPunc == state.context.type) popContext(state);
          }
          else if (curPunc == "." && state.context && state.context.type == "pattern") popContext(state);
          else if (/atom|string|variable/.test(style) && state.context) {
            if (/[\}\]]/.test(state.context.type))
              pushContext(state, "pattern", stream.column());
            else if (state.context.type == "pattern" && !state.context.align) {
              state.context.align = true;
              state.context.col = stream.column();
            }
          }

          return style;
        },

        indent: function(state, textAfter) {
          var firstChar = textAfter && textAfter.charAt(0);
          var context = state.context;
          if (/[\]\}]/.test(firstChar))
            while (context && context.type == "pattern") context = context.prev;

          var closing = context && firstChar == context.type;
          if (!context)
            return 0;
          else if (context.type == "pattern")
            return context.col;
          else if (context.align)
            return context.col + (closing ? 0 : 1);
          else
            return context.indent + (closing ? 0 : indentUnit);
        }
      };
    });

    CodeMirror.defineMIME("text/x-sql", "sql");

}