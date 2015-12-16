# The name of the panel to be added to HORIZON_CONFIG. Required.
PANEL = 'draas_restore_plugin_panel'
# The name of the dashboard the PANEL associated with. Required.
PANEL_DASHBOARD = 'project'
# The name of the panel group the PANEL is associated with.
PANEL_GROUP = 'dr_plugin_panel_group'

# Python panel class of the PANEL to be added.
ADD_PANEL = \
    'openstack_dashboard.dashboards.project.draas_restore.panel.DraasRestore'
