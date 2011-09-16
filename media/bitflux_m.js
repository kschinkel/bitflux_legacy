/*!
 * Ext JS Library 3.3.0
 * Copyright(c) 2006-2010 Ext JS, Inc.
 * licensing@extjs.com
 * http://www.extjs.com/license
 */

var store;
var engineStatus;
var selRecordList = new Array();
var viewport;
var controlBar;
var newDLBar;
var lenOfTopBut;
var statusB = '<img src="/site_media/bad.gif" />';
var statusG = '<img src="/site_media/good.gif" />';
var grid;
var dirStore;
var fileBrowser;
var fileBrowserSelModel = new Ext.grid.RowSelectionModel({singleSelect:true});
var changeDir;
var autoDLBrowser;
var autoDLStore;
var autoDLWindow;
var autoDLLogsWindow;
var tabs;
var CWD;
var selectEntry = null;
var canChangeDir = true;

var updateFreeSpace = function(){
    postData =""
    Ext.Ajax.request({
       url: '/freespace/',
       method: 'POST',
       params: postData,
       success: function(response, opts) {
          var obj = Ext.decode(response.responseText);
          fileBrowser.getBottomToolbar().getComponent('free_space').setText(obj["remaining"])
       },
       failure: function(response, opts) {
          console.log('server-side failure with status code ' + response.status);
       }
    });
}

var mkNewDir = function(){
    dirName = Ext.getCmp('mkDir').getValue();
    if (dirName != "New Folder"){
        var postData = "mkDir=" +dirName;
        selectEntry = Ext.getCmp('mkDir').getValue();
        Ext.getCmp('mkDir').setValue("New Folder");
        Ext.Ajax.request({
           url: '/newdir/?',
           method: 'POST',
           params: postData,
           success: function(response, opts) {
              var obj = Ext.decode(response.responseText);
                dirStore.reload({
                    params: {
                        'currentDir': CWD
                    }
               });
           },
           failure: function(response, opts) {
              console.log('server-side failure with status code ' + response.status);
           }
        });
    }
};

var delEntry = function(){
    var sel = fileBrowser.selModel.getSelected();
    if(sel != null){
        title = "Remove Entry";
        msg = "Are you sure you want to delete: " + sel.data.entryName.toString();
        Ext.Msg.confirm( "Remove Entry", msg,  function(btn){
            postData = 'rmEntry=' + CWD + sel.data.entryName.toString();
            if (btn == 'yes'){
                Ext.Ajax.request({
                   url: '/rmEntry/?',
                   method: 'POST',
                   params: postData,
                   success: function(response, opts) {
                        dirStore.reload({
                            params: {
                                'currentDir': CWD
                            }
                       });
                   },
                   failure: function(response, opts) {
                      console.log('server-side failure with status code ' + response.status);
                   }
                });
            }
        });
    }
};
var renameEntry = function(){
    dirName = Ext.getCmp('mkDir').getValue();
    if (dirName != "New Folder"){
        selectEntry = Ext.getCmp('mkDir').getValue();
        Ext.getCmp('mkDir').setValue("New Folder");
        
        var sel = fileBrowser.selModel.getSelected();
        if(sel != null){
            title = "Rename Entry";
            msg = "Are you sure you want to rename: " + sel.data.entryName.toString() + " to " + dirName;
            Ext.Msg.confirm( "Rename Entry", msg,  function(btn){
                postData = 'renameEntry=' + CWD + sel.data.entryName.toString() + '&newName='+dirName;
                if (btn == 'yes'){
                    Ext.Ajax.request({
                       url: '/renameEntry/?',
                       method: 'POST',
                       params: postData,
                       success: function(response, opts) {
                            dirStore.reload({
                                params: {
                                    'currentDir': CWD
                                }
                           });
                       },
                       failure: function(response, opts) {
                          console.log('server-side failure with status code ' + response.status);
                       }
                    });
                }
            });
        }
    }//end check if name is New Folder//
}
var updateEngineStatus = function(){
	var randomnumber=Math.floor(Math.random()*100);
	$.getJSON('/enginestatus/?'+randomnumber, function(data) { 
        if(data == 'up'){
            Ext.getCmp('engineStatus').update(statusG);
        }else{
            Ext.getCmp('engineStatus').update(statusB);
        }
	});
};

var updateAutoDLerStatus = function(){
    var randomnumber=Math.floor(Math.random()*100);
    $.getJSON('/autodlerstatus/?'+randomnumber, function(data) { 
        if(data == 'up'){
            Ext.getCmp('autoDLerStatus').update(statusG);
        }else{
            Ext.getCmp('autoDLerStatus').update(statusB);
        }
    });
};

var rowSelModel = new Ext.grid.RowSelectionModel({
    singleSelect:false,
    listeners: {
        rowselect: function(smObj, rowIndex, record) {
			if(record.data.queue_id !=0){
				//controlBar.items.get(8).enable();
				Ext.getCmp('qUp').enable();
			}else{
				//controlBar.items.get(8).disable();
				Ext.getCmp('qUp').disable();
			}
			if(record.data.queue_id < store.getTotalCount()-1){
				//controlBar.items.get(9).enable();
				Ext.getCmp('qDown').enable();
			}else{
				//controlBar.items.get(9).disable();
				Ext.getCmp('qDown').disable();
			}
			if(record.data.status == 'Stopped'){
				Ext.getCmp('startBtn').enable();
				Ext.getCmp('stopBtn').disable();
				//controlBar.items.get(3).enable();
				//controlBar.items.get(4).disable();
			}else if(record.data.status == 'Running'){
				Ext.getCmp('startBtn').disable();
				Ext.getCmp('stopBtn').enable();
				//controlBar.items.get(3).disable();
				//controlBar.items.get(4).enable();
			}else if(record.data.status == 'Queued'){
				Ext.getCmp('startBtn').enable();
				Ext.getCmp('stopBtn').enable();
			}else{
				Ext.getCmp('startBtn').disable();
				Ext.getCmp('stopBtn').disable();
			}
		if(selRecordList.indexOf(record.data.nid) == -1){
			selRecordList.push(record.data.nid);
		}
        },
		rowdeselect : function(smObj, rowIndex, record) {
			selRecordList.pop(record.data.nid);
		}
    }
});

var createLinkForDL = function(value, metaData, record) {
    if(record.get('isDir') == 'N') {
        //path = "download" + CWD +record.get('entryName') ;
        path =  "download/?downloadpath=" + CWD +record.get('entryName');
        return '<a href="'+path+'" style="color:#ffffff; text-decoration: none">'+record.get('entryName')+'</a>';
    }else{
        return record.get('entryName');
    }
};

updateDisplay = function() {
	store.reload();
	updateEngineStatus();
	updateAutoDLerStatus();
};

aNewDL = function(action){
	var postData = "newDL&" +action+"&URL=" +escape(newDLBar.items.get(0).getValue());
    postData += "&withAutoRename=" + Ext.getCmp('autoRenameChkBox').getValue();
	Ext.getCmp('newDLtxtField').setValue("");
	Ext.Ajax.request({
	   url: '/',
	   method: 'POST',
	   params: postData,
	   success: function(response, opts) {
		  var obj = Ext.decode(response.responseText);
	   },
	   failure: function(response, opts) {
		  console.log('server-side failure with status code ' + response.status);
	   }
	});
};

btnClicked = function(action){
	var selected = rowSelModel.getSelections();
	var postData = "";
	for ( var i=0;i<selected.length; ++i ){
		postData = postData + action+ "="+selected[i].data.nid.toString() + "&";
	}
	postData = "Action&" + postData;
	
	if(Ext.getCmp('withDataChkBox').getValue() && action == 'delete'){
		postData = postData+'DelWData';
	}
	if(action == 'cleanup'){
		postData = postData+'cleanup';
	}
	//console.log(postData);
	Ext.Ajax.request({
	   url: '/',
	   method: 'POST',
	   params: postData,
	   success: function(response, opts) {
		  var obj = Ext.decode(response.responseText);
		  //console.dir(obj);
	   },
	   failure: function(response, opts) {
		  console.log('server-side failure with status code ' + response.status);
	   }
	});
};

Ext.override(Ext.grid.GridView, {
    //Custom method to restore scrollTop functionality
    scrollTop : function() {
        this.scroller.dom.scrollTop = 0;
        this.scroller.dom.scrollLeft = 0;
    },
    scrollToTop : Ext.emptyFn
});

Ext.onReady(function(){
    controlBar = new Ext.Toolbar({
        //region: 'south',
        
        x: 0,
        y: 350,
        width:980,
        //anchor: '100%',
        items: [
            {xtype:'label',
                text: 'Engine Status:'	
            },
            {xtype:'tbtext',
                id:'engineStatus',
                text:''
            },
            '-'
            ,
            {xtype:'label',
                text: 'AutoDL Status:'	
            },
            {xtype:'tbtext',
                id:'autoDLerStatus',
                text:''
            },
            '->',
            {text: 'Clean Up',
                width: 50,
                height: 50,
                disabled:false,
                handler: function() {btnClicked('cleanup')}
            },
            '-'
            ,
            {text: 'Start',
                width: 50,
                height: 50,
                disabled:true,
                id:'startBtn',
                handler: function() {btnClicked('start')}
            },
            {text: 'Stop',
                width: 50,
                height: 50,
                id:'stopBtn',
                disabled:true,
                handler: function() {btnClicked('stop')}
            },
            {text: 'Queue',
                width: 50,
                height: 50,
                handler: function() {btnClicked('queue')}
            },
            '-',
            {text: 'Delete',
                width: 50,
                height: 50,
                handler: function() {btnClicked('delete')}
            },
            {boxLabel: 'With Data',
                xtype: 'checkbox',
                id: 'withDataChkBox',
                checked: true
            },
            '-',
            {xtype: 'tbbutton',
                cls:'x-btn-text-icon',
                icon :'/site_media/col-move-bottom.gif',
                id:'qUp',
                disabled:true,
                handler: function() {btnClicked('up')}
            },
            {xtype: 'tbbutton',
                cls:'x-btn-text-icon',
                id:'qDown',
                icon :'/site_media/col-move-top.gif',
                disabled:true,
                handler: function() {btnClicked('down')}
            }
        ]
    });

    newDLBar = new Ext.Toolbar({
        region: 'north',
        width:1000,
        height:30,
        items: [
            {xtype: 'textfield',
                id: 'newDLtxtField',
                width:800
            },
            '-',
            {boxLabel: 'Auto-Rename',
                xtype: 'checkbox',
                id: 'autoRenameChkBox',
                checked: true
            },
            '-',
            {text: 'Start',
                disabled:false,
                handler: function() {aNewDL('start')}
            },
            '-',
            {text: 'Add Pause',
                disabled:false,
                handler: function() {aNewDL('pause')}
            },
            '-',
            {text: 'Queue',
                disabled:false,
                handler: function() {aNewDL('queue')}
            },
            '-'
        ]
    });
        
    store = new Ext.data.JsonStore({
        root: 'downloads',
        totalProperty: 'total',
        fields: [
            'filename', 'total_size','queue_id','status','dl_speed','progress','eta','pid', 'nid', 'path'
        ],

        proxy: new Ext.data.HttpProxy({
            url: '/dlList/?',
            method: 'GET'
        }),
        listeners: {
            'load': {
                fn: function(obj,row) {
                    var row_indexes = new Array();
                    for(var i=0; i < selRecordList.length; i++ ){
                        var idx = store.find('nid', selRecordList[i]);
                        if(-1 !== idx) {
                            row_indexes.push( idx );
                        }     
                    }
                    rowSelModel.selectRows(row_indexes);
                }
            }
        }
    });
        


        
    dirStore = new Ext.data.JsonStore({
        root: 'dirList',
        totalProperty: 'total',
        fields: [
            'entryName', 'isDir','size','date'
        ],
        sortInfo: {field: 'entryName', direction: 'ASC'},
        proxy: new Ext.data.HttpProxy({
            //url: '/dirList/?currentDir='+currentDir,
            url: '/dirList/?',
            method: 'GET'
        }),
        listeners: {
            'load':{
                fn:function(obj,records,options ){     
                    
                    split = CWD.split("/");
                    bar = tabs.getTopToolbar();
                    bar.removeAll();
                    
                    bar.add({
                        xtype: "tbtext", 
                        text: "Current Directory:"
                    });
                    full_path = "/";
                    for( i = 0; i < split.length-1; i++){
                        label = split[i] + "/";
                        full_path += label;
                        bar.addButton({
                            text: label,
                            id: full_path,
                            listeners: {
                                'click': {
                                    fn:  function(obj) {
                                        path = obj.getId();
                                        path = path.substr(1);
                                        CWD = path;
                                        canChangeDir = false;
                                        dirStore.reload({
                                            params: {
                                                'currentDir': path
                                            }
                                        });
                                    },
                                    scope: this,
                                    delay: 100
                                }
                            }
                        });
                    }
                    //newDLBar.items.get(8).update(workingDir);
                    
                    bar.doLayout();
                    canChangeDir = true;
                    //Ext.getCmp('workingDir').update(workingDir);
                    
                    if (selectEntry != null){
						tabs.setActiveTab(1);
						fileBrowser.doLayout();
                        var index = dirStore.findExact('entryName',selectEntry);
                        fileBrowser.getSelectionModel().selectRow(index);               
                        fileBrowser.getView().focusRow(index);
                        selectEntry = null;
                    }
  
                    /*Make request for free space here*/
                    updateFreeSpace();                   
                }
            },
            scope: this,
            delay: 100
        }
    });
        
        //dirStore.reload();
        
    autoDLStore = new Ext.data.JsonStore({
        root: 'autoDLList',
        totalProperty: 'total',
        fields: [
            'entryName',
            'id',
            'latest_season',
            'latest_episode'
        ],

        proxy: new Ext.data.HttpProxy({
            url: '/autoDLList/?',
            method: 'GET'
        })
    });
        
        
    fileBrowser = new Ext.grid.GridPanel({
        width:450,
        height:350,
        title:'File Browser',
        region: 'center',
        store: dirStore,
        trackMouseOver:false,
        disableSelection:true,
        selModel: fileBrowserSelModel,
        // grid columns
        /*{header: "Dir?",
            dataIndex: 'isDir',
            sortable: true
        },*/
        columns:[
        {
            header: "Name",
            dataIndex: 'entryName',
            renderer : createLinkForDL,
            width: 450,
            sortable: true
        },
        {header: "Size",
            dataIndex: 'size',
           // width: 100,
            sortable: true
        },
        {header: "Date",
            dataIndex: 'date',
           // width: 100,
            sortable: true
        }],

        // customize view config
        viewConfig: {
            forceFit:true
        },
        // Listeners for clicking the rows
        listeners: {
            'rowdblclick':{
                fn:function(obj,row,ev){
                    the_entry = obj.getStore().getAt(row);
                    if (the_entry.data.isDir == 'Y' && canChangeDir){
                        param =  the_entry.data.entryName + "/";
                        CWD += param;
                        canChangeDir = false;
                        dirStore.reload({
                            params: {
                                'currentDir': CWD
                            }
                        });
                    }else if(the_entry.data.isDir == 'P'){
                        var param = the_entry.data.entryName.substr(0,the_entry.data.entryName.lastIndexOf('/'));
                        param = param.substr(0,param.lastIndexOf('/')+1);
                        dirStore.reload({
                            params: {
                                'currentDir': param
                            }
                        });
                    }
                },
                scope:this,
                delay:100
            }
        },
        bbar: new Ext.Toolbar({
            width:1000,
            height:30,
            items: [
                {xtype: 'textfield',
                    value: 'New Folder',
                    id: 'mkDir',
                    width:200
                },
                {text: 'New Dir',
                    handler: mkNewDir
                },
                '-'
                ,{text: 'Del Entry',
                    handler: delEntry
                },
                '-'
                ,{text: 'Rename Entry',
                    handler: renameEntry
                },
                '->',
                {xtype:'label',
                    text:'Remaining Space:'},
                {xtype:'tbtext',
                    text:'-',
                    id: 'free_space'
                }                
            ]            
        })
    });
    
    changeDir = new Ext.Window({
        title: 'Change Directory',
        plain: true,
        height: 400,
        width: 500,
        closeable: true,
        closeAction: 'hide',
        items:  fileBrowser
        /*items: new Ext.TabPanel({
            border:false,
            activeTab: 0,
            autoHeight: true,
            items: [
                fileBrowser
            ]
        })*/
    });

    autoDLStore.reload();

    autoDLBrowser = new Ext.grid.GridPanel({
        width:350,
        height:350,
        title:'Auto DL Browser',
        region: 'east',
        collapsible : true,
        collapsed : true,
        store: autoDLStore,
        trackMouseOver:false,
        disableSelection:true,
        id : 'autoDLerPanel',
        selModel: new Ext.grid.RowSelectionModel({singleSelect:true}),

        // grid columns
        columns:[{header: "Entry Name",
            width:150,
            dataIndex: 'entryName',
            sortable: true
        },
        {header: "Last Season Dled",
            dataIndex: 'latest_season',
            sortable: true
        },
        {header: "Last Episode Dled",
            dataIndex: 'latest_episode',
            sortable: true
        }],
        bbar: new Ext.Toolbar({
            width:1000,
            height:30,
            items: [
                {text: 'Add',
                    handler: function() {
                        autoDLWindow.show();
                    }
                },
                {text: 'Remove',
                handler: function(){
                    if( autoDLBrowser.selModel.hasSelection() ){
                        Ext.MessageBox.confirm("Confirm","Are you sure?", function(btn){
                            if(btn == 'yes'){
                                //rowSelModel.getSelections();
                                var selected = autoDLBrowser.selModel.getSelected();
                                var postData = "id="+selected.data.id.toString();
                                Ext.Ajax.request({
                                    url: '/removeautodl/?',
                                    method: 'POST',
                                    params: postData,
                                    success: function(response, opts) {
                                    //autoDLStore.reload();
                                    var obj = Ext.decode(response.responseText);
                                        //console.dir(obj);
                                    },
                                    failure: function(response, opts) {
                                        console.log('server-side failure with status code ' + response.status);
                                    }
                                });
                                //autoDLStore.reload();
                                //console.log(postData);
                            }//end of 'yes' button clicked'
                        });
                    }
                }
                },
                {text: 'Edit',
                disabled:true //TODO: have not implemented edit yet, just delete and create it again
                }
            ]
        }),
        listeners: {
            'rowdblclick':{
                fn:function(obj,row,ev){
                    the_entry = obj.getStore().getAt(row);
                    autoDLLogsStore.reload({
                        params: {
                            'id': the_entry.id
                        }
                    });
                    autoDLLogsWindow.show();
                },
                scope:this,
                delay:100
            }
        }
    });
        
    var autoDLLogsStore = new Ext.data.JsonStore({
        root: 'autoDLLogs',
        totalProperty: 'total',

        fields: [
            'notes', 'ts','season_num','episode_num'
        ],

        proxy: new Ext.data.HttpProxy({
            url: '/autoDLLog/?',
            method: 'GET'
        })
    });
        
    var autoDLLogsPanel = new Ext.grid.GridPanel({
        width:450,
        height:350,
        title:'Auto DL Entry Logs',
        region: 'center',
        //collapsible : true,
        store: autoDLLogsStore,
        trackMouseOver:false,
        disableSelection:true,
        selModel: new Ext.grid.RowSelectionModel({singleSelect:true}),
        // grid columns
        columns:[{header: "Notes",
            dataIndex: 'notes',
            sortable: true
        },
        {header: "Date/Time",
            dataIndex: 'ts',
            sortable: true
        },
        {header: "Season",
            dataIndex: 'season_num',
            sortable: true
        },
        {header: "Episode",
            dataIndex: 'episode_num',
            sortable: true
        }],

        // customize view config
        viewConfig: {
            forceFit:true
        }	
    });
        
    autoDLLogsWindow = new Ext.Window({
        layout:'fit',
        width:450,
        height:320,
        closeAction :'hide',
        resizable: true,
        closable:true,
        border:false,
        plain:true,
        xtype: 'container',
        items:autoDLLogsPanel
        /*onHide:function(){
            autoDLStore.reload();
        }*/
    });
        
    var autoDLForm = new Ext.form.FormPanel({
        title: 'Auto DL Entry',
        id:'autoDLForm',
        url:'/autodlnew/',
        bodyStyle: 'padding:15px',
        width: 350,
        defaultType: 'textfield',
        defaults: {
            // applied to each contained item
            width: 230,
            msgTarget: 'side'
        },
        items: [
                {fieldLabel: 'Name',
                name: 'autoDL_name',
                allowBlank: false,
                labelSeparator: ':' // override labelSeparator layout config
                },
                {xtype:'numberfield',
                fieldLabel: 'Season[0-999]; Currently does not increment',
                name: 'autoDL_season_start',
                width: 50,
                allowBlank: false,
                decimalPrecision : 0,
                minValue:0,
                maxValue:999,
                labelSeparator: ':' // override labelSeparator layout config
                },
                {xtype:'numberfield',
                fieldLabel: 'Episode Start From [0-999]; Will increment',
                name: 'autoDL_episode_start',
                width: 50,
                allowBlank: false,
                decimalPrecision : 0,
                minValue:0,
                maxValue:999,
                labelSeparator: ':' // override labelSeparator layout config
                }
        ],
        validResponse:function(form, action) {
            autoDLForm.getForm().reset();
            autoDLWindow.hide();
        },
        buttons: [
            {text: 'Submit',
                handler:function(args){
                    autoDLForm.getForm().submit({scope:autoDLForm, success:autoDLForm.validResponse,failure:autoDLForm.validResponse});
                }
            
            },
            {text: 'Cancel',
                handler:function(args){
                    autoDLForm.getForm().reset();
                    autoDLWindow.hide();
                }
            }
        ],
        layoutConfig: {
            labelSeparator: '~' // superseded by assignment below
        },
        // config options applicable to container when layout='form':
        hideLabels: false,
        labelAlign: 'left',   // or 'right' or 'top'
        labelSeparator: '>>', // takes precedence over layoutConfig value
        labelWidth: 150,       // defaults to 100
        labelPad: 8         // defaults to 5, must specify labelWidth to be honored
    });

    autoDLWindow = new Ext.Window({
        layout:'fit',
        width:450,
        height:320,
        closeAction :'hide',
        resizable: true,
        closable:true,
        border:false,
        plain:true,
        xtype: 'container',
        items:[autoDLForm]
        /*onHide:function(){
            autoDLStore.reload();
        }*/
    });
        
    // pluggable renders
    /*function renderTopic(value, p, record){
        return String.format(
                '<b><a href="http://extjs.com/forum/showthread.php?t={2}" target="_blank">{0}</a></b><a href="http://extjs.com/forum/forumdisplay.php?f={3}" target="_blank">{1} Forum</a>',
                value, record.data.forumtitle, record.id, record.data.forumid);
    }
    function renderLast(value, p, r){
        return String.format('{0}<br/>by {1}', value.dateFormat('M j, Y, g:i a'), r.data['lastposter']);
    }*/

    grid = new Ext.grid.GridPanel({
        width:980,
        height:350,
        x: 0,
        y: 0,
        //anchor:'100%',
        title:'Downloads',
        region: 'center',
        store: store,
        trackMouseOver:false,
        disableSelection:true,
        selModel: rowSelModel,
		
        // grid columns
        columns:[
        /*{
            header: "NID",
            dataIndex: 'nid',
            sortable: true
        },*/
        {header: "Filename",
            dataIndex: 'filename',
            width: 420,
            sortable: true
        },
        {header: "Total Size",
            dataIndex: 'total_size',
            //width: 100,
            sortable: true
        },
        {header: "Queue",
            dataIndex: 'queue_id',
           // width: 100,
            sortable: true
        },
        {header: "Status",
            dataIndex: 'status',
           // width: 100,
            sortable: true
        },
        {header: "DL Speed",
            dataIndex: 'dl_speed',
            //width: 100,
            sortable: true
        },
        {header: "%",
            dataIndex: 'progress',
            //width: 100,
            sortable: true
        },
        {header: "ETA",
            dataIndex: 'eta',
            width: 50,
            sortable: true
        }/*,
        {header: "PID",
            dataIndex: 'pid',
            sortable: true
        }*/],

        // customize view config
        /*viewConfig: {
            forceFit:true
        },*/
		listeners: {
            'rowdblclick':{
                fn:function(obj,row,ev){
                    the_entry = obj.getStore().getAt(row);
                    if ( canChangeDir){
                        CWD =  the_entry.data.path;
                        //CWD += param;
                        canChangeDir = false;
						selectEntry = the_entry.data.filename;
                        dirStore.reload({
                            params: {
                                'currentDir': CWD
                            }
                        });
						//TBD: change focus to filebrowser here
						/*tabs.setActiveTab(1);
						var index = dirStore.findExact('entryName',the_entry.data.filename);                     
						fileBrowser.getSelectionModel().selectRow(index);               
						fileBrowser.getView().focusRow(index);*/
					}
                },
                scope:this,
                delay:100
            }
        },
        // paging bar on the bottom
        bbar: new Ext.PagingToolbar({
            pageSize: 12,
            store: store,
            displayInfo: true,
            displayMsg: 'Displaying downloads {0} - {1} of {2}',
            emptyMsg: "No downloads to display"
        })
    });


    tabs = new Ext.TabPanel({
        //renderTo: Ext.getBody(),
        region: 'center',
        activeTab: 0,
        title:'Tabs',
        items: [grid,
                fileBrowser
                ],
        viewConfig: {
            forceFit:true
        },
        tbar: new Ext.Toolbar({
            width:1000,
            height:30,
            items: [
                {xtype:'tbtext',
                    text: '',
                    id:'workingDir'
                }
            ]            
        })
    });

});//End of ext.onReady()

initialize = function() {
	viewport = new Ext.Viewport({
        layout:'absolute',
        layoutConfig: {
            // layout-specific configs go here
            extraCls: 'x-abs-layout-item',
        },
        items: [
			//newDLBar,
			grid,
           //tabs,
           controlBar,
		   //autoDLBrowser
        ],
        //stateful: true,
		listeners: {
			'resize': {
				fn: function(obj,aW,aH,rW,rH) {
					if(rW != null){
						newDLBar.items.get(0).setWidth(rW-400);
					}
				}
			},
			'render': {
				fn: function(obj) {
					newDLBar.items.get(0).setWidth(obj.getWidth()-400);
				}
			}
		}
    });

    Ext.Ajax.request({
	   url: '/getCWD/?',
	   method: 'POST',
	   params: "",
	   success: function(response, opts) {
		  var obj = Ext.decode(response.responseText);
          CWD = obj;
          dirStore.reload({
                params: {
                    'currentDir': CWD
                }
           });
		  //console.dir(obj);
	   },
	   failure: function(response, opts) {
		  console.log('server-side failure with status code ' + response.status);
	   }
	});
    
    //fileBrowser.getBottomToolbar().doLayout();
    
    //CWD = "/";
    store.setDefaultSort('queue_id', 'ASC'); //'ASC' or 'DESC'
    
    tabs.setActiveTab(0);
	store.load({params:{start:0, limit:20}});
	window.setInterval('updateDisplay()',1000);
    updateFreeSpace(); 
};

