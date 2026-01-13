# Frappe Social Media Scheduler - Demo Guide

This guide walks through demonstrating the Facebook integration, posting workflow, and analytics viewing.

## Prerequisites

### 1. Facebook Developer App Setup

Before running the demo, you need a Facebook App configured:

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app (choose "Business" type)
3. Add the "Facebook Login" product
4. Configure OAuth settings:
   - **Valid OAuth Redirect URIs**: `https://airplane-mode.m.frappe.cloud/api/method/frappe_social.frappe_social.api.oauth.callback_facebook`
   - Enable **Client OAuth Login**
   - Enable **Web OAuth Login**

5. Get your App credentials:
   - App ID
   - App Secret

### 2. Facebook Page Required

⚠️ **Important**: Facebook personal profiles CANNOT post via API (Facebook policy since 2018). You must have a Facebook Page.

To create a test page:
1. Go to Facebook > Pages > Create New Page
2. Create a page for testing (e.g., "My Test Business Page")
3. You'll connect this page during OAuth

---

## Demo Walkthrough

### Step 1: Configure API Credentials

1. Navigate to: **Frappe Social > Social Settings**
   - Direct URL: `/app/social-settings`

2. Fill in the **Meta (Facebook/Instagram)** section:
   - **App ID**: Your Facebook App ID
   - **App Secret**: Your Facebook App Secret
   - **Graph API Version**: `v21.0` (default)

3. Click **Save**

![Social Settings Screenshot](https://via.placeholder.com/800x400?text=Social+Settings+Screen)

---

### Step 2: Connect Facebook Page (OAuth)

1. Navigate to: **Frappe Social > Social Integration**
   - Direct URL: `/app/social-integration`

2. Click the **"Connect Account"** button (primary blue button)

3. In the dialog:
   - Select **Facebook** from the dropdown
   - Note the warning about personal profiles not being supported
   - Click **Connect**

4. A popup window opens with Facebook OAuth:
   - Log in to Facebook (if not already)
   - **Select the Pages** you want to connect
   - Grant all requested permissions:
     - `pages_manage_posts`
     - `pages_read_engagement`
     - `pages_show_list`
     - `business_management`

5. After authorization:
   - If you have **one page**: Automatically redirected to the integration view
   - If you have **multiple pages**: Shown a page selection screen

6. Verify the integration:
   - **Connection Status**: Should show "Connected" (green)
   - **Profile Name**: Your Facebook Page name
   - **Account Type**: Page
   - **Token Expiry**: ~60 days from now

**Demo Tip**: Show the "Test Connection" button to verify the OAuth token is working.

---

### Step 3: Create and Publish a Post

1. Navigate to: **Frappe Social > Social Post**
   - Direct URL: `/app/social-post`

2. Click **+ Add Social Post**

3. Fill in the post details:
   - **Content**: Enter your post text
     ```
     🚀 Testing our new social media scheduler! 
     
     This post was published directly from our Frappe/ERPNext system.
     
     #Automation #ERPNext #FrappeSocial
     ```
   - **Note**: HTML formatting from the editor will be stripped automatically

4. Add platforms:
   - In the **Platforms** table, click "Add Row"
   - **Platform**: Select "Facebook"
   - **Integration**: Select your connected Facebook Page

5. Choose publishing method:

   **Option A: Publish Now (Demo)**
   - Leave **Scheduled Time** empty
   - Click **Save**, then **Submit**
   - Click the **"Publish Now"** button
   - Status changes: Draft → Published

   **Option B: Schedule for Later**
   - Set **Scheduled Time** to a future date/time
   - Click **Save**, then **Submit**
   - Status changes: Draft → Scheduled
   - Post will be published automatically by the scheduler

6. Verify the post:
   - **Status**: Should show "Published" (green)
   - **Published Time**: Shows when it was published
   - Check your Facebook Page to see the live post!

---

### Step 4: View Analytics

#### Account-Level Analytics

1. Navigate to: **Frappe Social > Social Analytics**
   - Direct URL: `/app/social-analytics`

2. View daily metrics for connected accounts:
   - Followers count
   - Impressions
   - Engagement rate
   - Likes, comments, shares

3. To fetch fresh analytics:
   - Open a **Social Integration** record
   - Click **"Fetch Analytics"** button
   - New Social Analytics record is created for today

#### Post-Level Analytics

1. Navigate to: **Frappe Social > Social Post Analytics**
   - Direct URL: `/app/social-post-analytics`

2. View per-post performance:
   - Impressions
   - Reach
   - Engagement rate
   - Likes, comments, shares, saves, clicks

#### Reports

1. **Post Performance Report**
   - URL: `/app/query-report/Post%20Performance`
   - Shows all posts with their engagement metrics
   - Filter by platform, date range, status

2. **Account Growth Report**
   - URL: `/app/query-report/Account%20Growth`
   - Shows follower trends over time
   - Compare performance across platforms

3. **Publishing Summary Report**
   - URL: `/app/query-report/Publishing%20Summary`
   - Overview of posts by status
   - Success vs failure rates

---

## Quick Demo Script (5 minutes)

For a quick demo, follow this condensed flow:

### Setup (Already Done Before Demo)
- API credentials configured in Social Settings
- Facebook Page already connected

### Live Demo Steps

1. **Show Workspace** (30 sec)
   - Navigate to Frappe Social workspace
   - Point out the main sections

2. **Show Connected Account** (30 sec)
   - Open Social Integration list
   - Show the connected Facebook Page with green "Connected" status

3. **Create & Publish Post** (2 min)
   - Create new Social Post
   - Add engaging content
   - Select Facebook integration
   - Save, Submit, Publish Now
   - Show success message

4. **Verify on Facebook** (30 sec)
   - Open Facebook Page in new tab
   - Show the post is live

5. **Show Analytics** (1.5 min)
   - Open Post Performance Report
   - Show Account Growth Report
   - Briefly show Social Analytics list

---

## Troubleshooting Common Issues

### OAuth Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "No Facebook Pages found" | User has no Pages | Create a Facebook Page first |
| "Token exchange failed" | App credentials wrong | Verify App ID and Secret in Social Settings |
| "Invalid redirect URI" | OAuth misconfigured | Add callback URL to Facebook App settings |

### Publishing Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "(#200) Permissions error" | Missing permissions | Reconnect with all permissions granted |
| "Session expired" | Token expired | Reconnect the integration |
| "Rate limit exceeded" | Too many posts | Wait and retry, or upgrade API tier |

### Analytics Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Insights not available" | Need Page Insights permission | Reconnect with `pages_read_engagement` |
| "No data returned" | Too early after posting | Wait 24 hours for insights to populate |

---

## API Callback URLs Reference

For your Facebook App OAuth settings, use these callback URLs:

| Platform | Callback URL |
|----------|-------------|
| Facebook | `{site_url}/api/method/frappe_social.frappe_social.api.oauth.callback_facebook` |
| Instagram | `{site_url}/api/method/frappe_social.frappe_social.api.oauth.callback_instagram` |
| Twitter | `{site_url}/api/method/frappe_social.frappe_social.api.oauth.callback_twitter` |
| LinkedIn | `{site_url}/api/method/frappe_social.frappe_social.api.oauth.callback_linkedin` |
| YouTube | `{site_url}/api/method/frappe_social.frappe_social.api.oauth.callback_youtube` |

Replace `{site_url}` with your actual site URL (e.g., `https://airplane-mode.m.frappe.cloud`)

---

## Next Steps After Demo

1. **Connect more platforms**: Try LinkedIn, Instagram
2. **Test scheduling**: Create a scheduled post for the future
3. **Set up analytics cron**: Enable automatic analytics fetching
4. **Add team members**: Grant Social Manager role to users
