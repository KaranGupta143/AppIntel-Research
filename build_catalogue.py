"""One-off helper: writes data/apps.json from the assignment list. Not part of the research pipeline."""
import json
RAW = {
"CRM and Sales": "Salesforce|salesforce.com;HubSpot|hubspot.com;Pipedrive|pipedrive.com;Attio|attio.com;Twenty|twenty.com;Podio|podio.com;Zoho CRM|zoho.com;Close|close.com;Copper|copper.com;DealCloud|api.docs.dealcloud.com",
"Support and Helpdesk": "Zendesk|zendesk.com;Intercom|intercom.com;Freshdesk|freshdesk.com;Front|front.com;Pylon|usepylon.com;LiveAgent|liveagent.com;Plain|plain.com;Help Scout|helpscout.com;Gorgias|gorgias.com;Gladly|gladly.com",
"Communications and Messaging": "Slack|slack.com;Twilio|twilio.com;Zoho Cliq|zoho.com;Lark (Larksuite)|open.larksuite.com;Pumble|pumble.com;Discord|discord.com;Telegram|core.telegram.org;WhatsApp Business|developers.facebook.com;Aircall|aircall.io;Vonage|developer.vonage.com",
"Marketing, Ads, Email and Social": "Google Ads|developers.google.com;Meta Ads|developers.facebook.com;LinkedIn Ads|learn.microsoft.com;GoHighLevel|highlevel.stoplight.io;Mailchimp|mailchimp.com;Klaviyo|developers.klaviyo.com;systeme.io|systeme.io;Pinterest|developers.pinterest.com;Threads (Meta)|developers.facebook.com;SendGrid|sendgrid.com",
"Ecommerce": "Shopify|shopify.dev;WooCommerce|woocommerce.com;BigCommerce|developer.bigcommerce.com;Salesforce Commerce Cloud|developer.salesforce.com;Magento (Adobe Commerce)|developer.adobe.com;Squarespace|developers.squarespace.com;Ecwid|api-docs.ecwid.com;Gumroad|gumroad.com;Amazon Selling Partner|developer-docs.amazon.com;fanbasis|fanbasis.com",
"Data, SEO and Scraping": "DataForSEO|docs.dataforseo.com;SE Ranking|seranking.com;Ahrefs|ahrefs.com;MrScraper|docs.mrscraper.com;Apify|docs.apify.com;Firecrawl|firecrawl.dev;Bright Data|brightdata.com;Sherlock|github.com;Waterfall.io|waterfall.io;Clay|clay.com",
"Developer, Infra and Data platforms": "GitHub|docs.github.com;Vercel|vercel.com;Netlify|docs.netlify.com;Cloudflare|developers.cloudflare.com;Supabase|supabase.com;Neo4j|neo4j.com;Snowflake|docs.snowflake.com;MongoDB Atlas|mongodb.com;Datadog|docs.datadoghq.com;Sentry|docs.sentry.io",
"Productivity and Project Management": "Notion|developers.notion.com;Airtable|airtable.com;Linear|developers.linear.app;Jira|developer.atlassian.com;Asana|developers.asana.com;Monday.com|developer.monday.com;ClickUp|clickup.com;Coda|coda.io;Smartsheet|smartsheet.com;Harvest|help.getharvest.com",
"Finance and Fintech": "Stripe|stripe.com;Plaid|plaid.com;Binance|binance-docs.github.io;Paygent Connect|paygent.co.jp;iPayX|ipayx.ai;QuickBooks|developer.intuit.com;Xero|developer.xero.com;Brex|developer.brex.com;Ramp|docs.ramp.com;PitchBook|pitchbook.com",
"AI, Research and Media-native": "NotebookLM|cloud.google.com;Otter AI|help.otter.ai;Fathom|fathom.video;Consensus|consensus.app;Reducto|reducto.ai;Devin|docs.devin.ai;higgsfield|higgsfield.ai;Mermaid CLI|github.com;YouTube Transcript|transcriptapi.com;Grain|grain.com",
}
apps, i = [], 1
for cat, row in RAW.items():
    for item in row.split(";"):
        name, dom = item.split("|")
        apps.append({"id": i, "name": name, "category": cat, "domain_hint": dom}); i += 1
assert len(apps) == 100
json.dump(apps, open("data/apps.json", "w"), indent=2)
print(len(apps), "apps written")
