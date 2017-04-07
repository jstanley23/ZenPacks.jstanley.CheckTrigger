Ext.onReady(function(){
Ext.ns("Zenoss.CheckTrigger.dialogs")

var gridId = "events_grid";

function getSelectedEvids() {
    var grid = Ext.getCmp(gridId),
        selected = grid.selModel.getSelection();
    return Ext.pluck(Ext.Array.map(selected, function(value, ind, array) { return value.getData() }), 'evid');
}

function getSelectedEvents() {
    var grid = Ext.getCmp(gridId);
    return grid.getSelectionModel().getSelection();
}

function cbChange(obj) {
    var cbs = document.getElementsByClassName("styleTypeCheckBoxes");
    for (var i = 0; i < cbs.length; i++) {
        cbs[i].checked = false;
    }
    obj.checked = true;
}

var addCheckTriggerButton = function(event_grid) {
    var eventsToolbar = event_grid.tbar;

    var createCheckTriggerButton = new Ext.Button({
        id: Ext.id('','create-checktrigger-button'),
        text: 'Check Event',
        menu: {
            items: [{
                id: 'style_radio',
                xtype: 'radiogroup',
                columns: 1,
                items: [{
                    boxLabel: _t('Human Readable Output'),
                    name: 'style_item',
                    inputValue: 'human',
                },{
                    boxLabel: _t('CSV Output'),
                    name: 'style_item',
                    inputValue: 'csv',
                },{
                    boxLabel: _t('Summary Output'),
                    name: 'style_item',
                    inputValue: 'summary',
                    checked: true,
                }]
            },{
                xtype: 'menuseparator'
            },{
                text: 'Test against all triggers',
                tooltip: 'Test against all triggers',
                handler: function() {
                    var style = Ext.ComponentQuery.query('[name=style_item]')[0].getGroupValue();
                    var win = new Zenoss.CommandWindow({
                        uids: { 'evids': getSelectedEvids(), 'trigger': 'all', 'style': style },
                        target: 'checkTriggerCommandView',
                        title: _t('Checking events against trigger(s)...')
                    });
                    win.show();
                }
            },{
                xtype: 'menuseparator'
            }]
        }
    });

    Zenoss.remote.CheckTriggerRouter.getTriggers({}, function(response) {
        Ext.each(JSON.parse(response.data), function(trigger) {
            var menuItem = createCheckTriggerButton.menu.add({
                text: trigger["name"],
                id: trigger["id"],
                tooltip: 'Check event(s) against ' + trigger["name"],
                handler: function() {
                    var style = Ext.ComponentQuery.query('[name=style_item]')[0].getGroupValue();
                    var win = new Zenoss.CommandWindow({
                        uids: { 'evids': getSelectedEvids(), 'trigger': trigger["name"], 'style': style },
                        target: 'checkTriggerCommandView',
                        title: _t('Checking events against trigger(s)...')
                    });
                    win.show();
                }
            });
        });
    });
    event_grid.child(0).add(createCheckTriggerButton);
    return createCheckTriggerButton;
};

var setupCheckTriggerButton = function(event_grid) {
    var new_grid = Ext.getCmp('events_grid');
    var createCheckTriggerButton = addCheckTriggerButton(new_grid);
    new_grid.on('selectionchange', function(selectionmodel) {
        var newDisabledValue = !selectionmodel.hasSelection() && selectionmodel.selectState !== 'All',
            history_combo = Ext.getCmp('history_combo'),
            archive = Ext.isDefined(history_combo) ? history_combo.getValue() === 1 : false;
        if (archive) {
            createCheckTriggerButton.setDisabled(true);
        } else {
            createCheckTriggerButton.setDisabled(newDisabledValue);
        }
    });
    new_grid.on('recreateGrid', setupCheckTriggerButton)
}

Ext.ComponentMgr.onAvailable('events_grid', setupCheckTriggerButton);

});
