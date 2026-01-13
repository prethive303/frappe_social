app_name = "frappe_social"
app_title = "Frappe Social"
app_publisher = "Macrobian"
app_description = "Social media scheduling and analytics module for Frappe/ERPNext"
app_email = "info@macrobian.com"
app_license = "MIT"
app_version = "1.0.0"

required_apps = ["frappe"]

# Installation
after_install = "frappe_social.install.after_install"

# Scheduled Tasks
scheduler_events = {
    "cron": {
        # Every minute - check for posts to publish
        "* * * * *": ["frappe_social.frappe_social.tasks.publish_scheduled_posts"],
        # Daily at midnight - reset rate limit counters
        "0 0 * * *": ["frappe_social.frappe_social.tasks.reset_rate_limit_counters"],
    },
    # Hourly - refresh expiring tokens AND fetch analytics
    "hourly": [
        "frappe_social.frappe_social.tasks.refresh_expiring_tokens",
        "frappe_social.frappe_social.tasks.fetch_daily_analytics",
        "frappe_social.frappe_social.tasks.fetch_post_analytics",
    ],
}
