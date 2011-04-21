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
var changeDir;
var autoDLBrowser;
var autoDLStore;
var autoDLWindow;
var autoDLLogsWindow;
var tabs;
var CWD;

var mkNewDir = function(){
	var postData = "mkDir=" +Ext.getCmp('mkDir').getValue();
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

var updateEngineStatus = function(){
	var randomnumber=Math.floor(Math.random()*100);
	$.getJSON('/enginestatus/?'+randomnumber, function(data) { 
	//var array = JSON.parse(data);
	if(data == 'up'){
		Ext.getCmp('engineStatus').update(statusG);
	}else{
		Ext.getCmp('engineStatus').update(statusB);
	}
	
	});
};
var updateAutoDLerStatus = function(){
	if(Ext.getCmp('autoDLerPanel').isVisible()){
		autoDLStore.reload();
		var randomnumber=Math.floor(Math.random()*100);
		$.getJSON('/autodlerstatus/?'+randomnumber, function(data) { 
			if(data == 'up'){
				Ext.getCmp('autoDLerStatus').update(statusG);
			}else{
				Ext.getCmp('autoDLerStatus').update(statusB);
			}
			});
	}
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
									}else{
										Ext.getCmp('startBtn').disable();
										Ext.getCmp('stopBtn').disable();
									}
								
								if(selRecordList.indexOf(rowIndex) == -1){
									selRecordList.push(rowIndex);
								}	
							},
							rowdeselect : function(smObj, rowIndex, record) {
								selRecordList.pop(rowIndex);
							}
					}
				}),
updateDisplay = function() {
	store.reload();
	//engineStatus.reload();
	updateEngineStatus();
	updateAutoDLerStatus();
};
aNewDL = function(action){
	var postData = "newDL&" +action+"&URL=" +escape(newDLBar.items.get(0).getValue());
    postData += "&withAutoRename=" + Ext.getCmp('autoRenameChkBox').getValue();
	//newDLBar.items.get(0).setValue("");
	Ext.getCmp('newDLtxtField').setValue("");
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

btnClicked = function(action){
	var selected = rowSelModel.getSelections();
	var postData = "";
	for ( var i=0;i<selected.length; ++i ){
		postData = postData + action+ "="+selected[i].data.queue_id.toString() + "&";
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
}

Ext.onReady(function(){
    controlBar = new Ext.Toolbar({
    region: 'south',
    width:1000,
    height:50,
    items: [
		{xtype:'label',
			text: 'Engine Status:'	
		},
		{xtype:'tbtext',
			id:'engineStatus',
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
		'-',
		/*{text: 'Current Dir:',
			disabled:true,
			handler: function() {
				dirStore.reload();
				changeDir.show();
			}
		},
		{xtype:'tbtext',
			text: '',
			id:'workingDir'
		},*/
    ]
});
	
	store = new Ext.data.JsonStore({
        root: 'downloads',
        totalProperty: 'total',
        //remoteSort: true,

        fields: [
            'filename', 'total_size','queue_id','status','dl_speed','progress','eta','pid'
        ],

        // load using script tags for cross domain, if the data in on the same domain as
        // this page, an HttpProxy would be better
        proxy: new Ext.data.HttpProxy({
            //url: 'http://kyle-server/myview/?'
			url: '/myview/?',
			method: 'GET'
        }),
		listeners: {
			'load': {
				fn: function(obj,row) {
					rowSelModel.selectRows(selRecordList);
				}
			}
		}
    });
	
    store.setDefaultSort('queue_id', 'ASC'); //'ASC' or 'DESC'

	
	dirStore = new Ext.data.JsonStore({
        root: 'dirList',
        totalProperty: 'total',

        fields: [
            'entryName', 'isDir','size','date'
        ],

        // load using script tags for cross domain, if the data in on the same domain as
        // this page, an HttpProxy would be better
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
                    bar.removeAll()
                    
                    bar.add({
                        xtype: "tbtext", 
                        text: "Current Directory:"
                    });
                    full_path = "/"
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
                                        //bytehive.files.selectByButton(obj);
                                        CWD = path;
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
					//Ext.getCmp('workingDir').update(workingDir);
				}
			}
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

        // load using script tags for cross domain, if the data in on the same domain as
        // this page, an HttpProxy would be better
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
		//collapsible : true,
        store: dirStore,
        trackMouseOver:false,
        disableSelection:true,
		selModel: new Ext.grid.RowSelectionModel({singleSelect:true}),

        // grid columns
        columns:[/*{header: "Dir?",
            dataIndex: 'isDir',
            sortable: true
        },*/
		{
            header: "Name",
            dataIndex: 'entryName',
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
					if (the_entry.data.isDir == 'Y'){
						param =  the_entry.data.entryName + "/";
                        CWD += param;
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
					},
					'->',
					{xtype:'label',
						text: 'Status:'	
					},
					{xtype:'tbtext',
						id:'autoDLerStatus',
						text:''
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

        // load using script tags for cross domain, if the data in on the same domain as
        // this page, an HttpProxy would be better
        proxy: new Ext.data.HttpProxy({
			//url: '/dirList/?currentDir='+currentDir,
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
        items:autoDLLogsPanel,
		/*onHide:function(){
			autoDLStore.reload();
		}*/
	});
	
	
	//autoDLWindow = new Ext.Window({
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
        items:[autoDLForm],
		/*onHide:function(){
			autoDLStore.reload();
		}*/
	});
	
    // pluggable renders
    function renderTopic(value, p, record){
        return String.format(
                '<b><a href="http://extjs.com/forum/showthread.php?t={2}" target="_blank">{0}</a></b><a href="http://extjs.com/forum/forumdisplay.php?f={3}" target="_blank">{1} Forum</a>',
                value, record.data.forumtitle, record.id, record.data.forumid);
    }
    function renderLast(value, p, r){
        return String.format('{0}<br/>by {1}', value.dateFormat('M j, Y, g:i a'), r.data['lastposter']);
    }

    grid = new Ext.grid.GridPanel({
        width:1000,
        //height:500,
        title:'Downloads',
		region: 'center',
        store: store,
        trackMouseOver:false,
        disableSelection:true,
		selModel: rowSelModel,

        // grid columns
        columns:[{
            header: "Filename",
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
            //width: 100,
            sortable: true
        }/*,
		{header: "PID",
            dataIndex: 'pid',
            sortable: true
        }*/],

        // customize view config
        viewConfig: {
            forceFit:true
        },

        // paging bar on the bottom
        bbar: new Ext.PagingToolbar({
            pageSize: 20,
            store: store,
            displayInfo: true,
            displayMsg: 'Displaying downloads {0} - {1} of {2}',
            emptyMsg: "No downloads to display"
        })
    });
    /*TRYING TO IMPLIMENT TABS*/
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
	//create the viewport to render everything

    
});



initialize = function() {
	viewport = new Ext.Viewport({
        layout: 'border',
        items: [
			newDLBar,
			//grid,
           tabs,
           controlBar,
		   autoDLBrowser
        ],
        stateful: true,
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
    
    //CWD = "/";
    tabs.setActiveTab(0);
	store.load({params:{start:0, limit:20}});
    dirStore.setDefaultSort('entryName', 'ASC');
	window.setInterval('updateDisplay()',1000);
};

