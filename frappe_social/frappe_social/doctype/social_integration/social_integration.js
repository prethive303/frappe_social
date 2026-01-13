// Copyright (c) 2024, Frappe Social and contributors
// For license information, please see license.txt

frappe.ui.form.on('Social Integration', {
    refresh: function (frm) {
        // Block manual creation - redirect to list
        if (frm.is_new()) {
            frappe.show_alert({
                message: __('Use "Connect Account" button to add integrations'),
                indicator: 'orange'
            });
            frappe.set_route('List', 'Social Integration');
            return;
        }

        // Add Connect button for disconnected integrations
        if (frm.doc.connection_status !== 'Connected') {
            frm.add_custom_button(__('Connect Account'), function () {
                frm.trigger('connect_account');
            }, __('Actions'));
        }

        // Add buttons for connected integrations
        if (frm.doc.connection_status === 'Connected') {
            frm.add_custom_button(__('Disconnect'), function () {
                frm.trigger('disconnect_account');
            }, __('Actions'));

            frm.add_custom_button(__('Test Connection'), function () {
                frm.trigger('test_connection');
            }, __('Actions'));

            frm.add_custom_button(__('Fetch Analytics'), function () {
                frm.trigger('fetch_analytics');
            }, __('Actions'));
        }

        // Show authorized user info
        if (frm.doc.authorized_user_name) {
            frm.set_intro(__('Authorized via: {0}', [frm.doc.authorized_user_name]), 'blue');
        }

        // Show connection status indicator
        frm.trigger('update_status_indicator');
    },

    connect_account: function (frm) {
        frappe.call({
            method: 'frappe_social.frappe_social.api.oauth.initiate_oauth',
            args: {
                platform: frm.doc.platform,
                integration: frm.doc.name
            },
            callback: function (r) {
                if (r.message && r.message.authorization_url) {
                    const popup = window.open(
                        r.message.authorization_url,
                        'oauth_popup',
                        'width=600,height=700,scrollbars=yes'
                    );

                    frappe.show_alert({
                        message: __('Complete authorization in the popup window'),
                        indicator: 'blue'
                    });

                    const pollTimer = setInterval(function () {
                        if (popup.closed) {
                            clearInterval(pollTimer);
                            frm.reload_doc();
                        }
                    }, 1000);
                }
            }
        });
    },

    disconnect_account: function (frm) {
        frappe.confirm(
            __('Are you sure you want to disconnect this account?'),
            function () {
                frappe.call({
                    method: 'frappe_social.frappe_social.api.oauth.disconnect',
                    args: { integration: frm.doc.name },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Account disconnected'),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            }
        );
    },

    test_connection: function (frm) {
        frappe.call({
            method: 'frappe_social.frappe_social.api.oauth.test_connection',
            args: { integration: frm.doc.name },
            callback: function (r) {
                if (r.message) {
                    if (r.message.valid) {
                        frappe.show_alert({
                            message: __('Connection is valid'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('Connection failed: ') + r.message.reason,
                            indicator: 'red'
                        });
                    }
                    frm.reload_doc();
                }
            }
        });
    },

    fetch_analytics: function (frm) {
        frappe.call({
            method: 'frappe_social.frappe_social.api.analytics.fetch_analytics',
            args: { integration: frm.doc.name },
            freeze: true,
            freeze_message: __('Fetching analytics...'),
            callback: function (r) {
                if (r.message) {
                    if (r.message.success) {
                        frappe.show_alert({
                            message: __('Analytics fetched successfully'),
                            indicator: 'green'
                        });
                        if (r.message.analytics_doc) {
                            frappe.set_route('Form', 'Social Analytics', r.message.analytics_doc);
                        }
                    } else {
                        frappe.show_alert({
                            message: __('Failed to fetch analytics: ') + (r.message.error_message || 'Unknown error'),
                            indicator: 'red'
                        });
                    }
                }
            }
        });
    },

    update_status_indicator: function (frm) {
        let indicator = 'grey';
        let status = frm.doc.connection_status;

        if (status === 'Connected') indicator = 'green';
        else if (status === 'Expired') indicator = 'orange';
        else if (status === 'Error') indicator = 'red';

        frm.page.set_indicator(status, indicator);
    }
});
