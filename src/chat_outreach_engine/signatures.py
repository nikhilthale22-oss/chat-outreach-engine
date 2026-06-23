"""Chat-vendor signature library.

Two tiers of signals:

LAYER 1 (raw HTML substring match, MUST be high-precision):
  - script_patterns: vendor-specific URLs that appear in <script src="...">
  - iframe_patterns: vendor-specific URLs that appear in <iframe src="...">
  - api_call_patterns: distinctive JS API calls/config object names that won't collide
                       with anything else (e.g. `window.intercomSettings`, `Tawk_API`)

LAYER 2 (rendered browser, can be looser):
  - runtime_globals: window.X variable names — only checked once page is fully loaded
  - dom_selectors:   CSS selectors querying actual DOM elements

NEVER use as a Layer-1 signal:
  - class names alone (e.g. /Beacon/i matches `navigator.sendBeacon`)
  - id names alone (e.g. /launcher/i matches every Shopify theme's launcher)
  - vendor name as a generic word (e.g. /yellow/i matches the color)
  - Shopify-internal substrings (e.g. /_support/i matches `themes_support`)

The hard rule: a Layer-1 signal must be something that CANNOT plausibly appear on a
random Shopify store's homepage unless that vendor's script is actually loaded.
"""
import re

VENDORS = [
    # ---------- LIVE CHAT ----------
    {"vendor": "intercom", "category": "live-chat",
     "script_patterns": [r"widget\.intercom\.io", r"intercomcdn\.com", r"api-iam\.intercom\.io"],
     "iframe_patterns": [r"intercom-sheets\.com"],
     "api_call_patterns": [r"window\.intercomSettings\b", r"Intercom\(\s*['\"]boot['\"]"],
     "runtime_globals": ["Intercom", "intercomSettings"],
     "dom_selectors": ["#intercom-container", ".intercom-lightweight-app", "#intercom-frame", ".intercom-launcher", 'iframe[name="intercom-messenger-frame"]']},

    {"vendor": "drift", "category": "live-chat",
     "script_patterns": [r"js\.driftt\.com", r"drift\.com/include"],
     "iframe_patterns": [],
     "api_call_patterns": [r"drift\.load\(", r"window\.drift\s*="],
     "runtime_globals": ["drift", "driftt"],
     "dom_selectors": ["#drift-widget", "#drift-frame", 'iframe[id^="drift-"]']},

    {"vendor": "crisp", "category": "live-chat",
     "script_patterns": [r"client\.crisp\.chat"],
     "iframe_patterns": [],
     "api_call_patterns": [r"window\.\$crisp\b", r"\bCRISP_WEBSITE_ID\b"],
     "runtime_globals": ["$crisp", "CRISP_WEBSITE_ID"],
     "dom_selectors": [".crisp-client", "#crisp-chatbox"]},

    {"vendor": "tawk.to", "category": "live-chat",
     "script_patterns": [r"embed\.tawk\.to"],
     "iframe_patterns": [r"tawk\.to"],
     "api_call_patterns": [r"\bTawk_API\b", r"\bTawk_LoadStart\b"],
     "runtime_globals": ["Tawk_API", "Tawk_LoadStart"],
     "dom_selectors": [".tawk-min-container", "#tawk-bubble-container"]},

    {"vendor": "livechat", "category": "live-chat",
     "script_patterns": [r"cdn\.livechatinc\.com", r"connect\.livechatinc\.com"],
     "iframe_patterns": [r"livechatinc\.com"],
     "api_call_patterns": [r"\bLiveChatWidget\b", r"window\.__lc\s*="],
     "runtime_globals": ["LiveChatWidget", "__lc", "LC_API"],
     "dom_selectors": ["#chat-widget-container"]},

    {"vendor": "olark", "category": "live-chat",
     "script_patterns": [r"static\.olark\.com"],
     "iframe_patterns": [],
     "api_call_patterns": [r"olark\.identify\(", r"olark\.configure\("],
     "runtime_globals": ["olark"],
     "dom_selectors": ["#olark-wrapper", "#habla_window_div"]},

    {"vendor": "tidio", "category": "live-chat",
     "script_patterns": [r"code\.tidio\.co", r"widget-v4\.tidiochat\.com"],
     "iframe_patterns": [r"tidio\.co", r"tidiochat\.com"],
     "api_call_patterns": [r"\btidioChatCode\b", r"\btidioChatApi\b"],
     "runtime_globals": ["tidioChatApi", "tidioChat"],
     "dom_selectors": ["#tidio-chat", "#tidio-chat-iframe"]},

    {"vendor": "chatra", "category": "live-chat",
     "script_patterns": [r"call\.chatra\.io"],
     "iframe_patterns": [r"chatra\.io"],
     "api_call_patterns": [r"\bChatraID\b", r"\bChatraSetup\b"],
     "runtime_globals": ["ChatraID", "Chatra", "ChatraSetup"],
     "dom_selectors": ["#chatra", "#chatra__iframe"]},

    {"vendor": "smartsupp", "category": "live-chat",
     "script_patterns": [r"smartsupp\.com/loader"],
     "iframe_patterns": [r"smartsuppchat\.com"],
     "api_call_patterns": [r"\b_smartsupp\b", r"window\.smartsupp\b"],
     "runtime_globals": ["smartsupp", "_smartsupp_key"],
     "dom_selectors": ["#smartsupp-widget-container"]},

    {"vendor": "jivochat", "category": "live-chat",
     "script_patterns": [r"code\.jivosite\.com", r"cdn\.jivochat\.com"],
     "iframe_patterns": [r"jivosite\.com", r"jivochat\.com"],
     "api_call_patterns": [r"\bjivo_api\b", r"\bjivo_init\b"],
     "runtime_globals": ["jivo_api", "jivo_init", "JivoSite"],
     "dom_selectors": ["#jivo-iframe-container", "jdiv"]},

    {"vendor": "purechat", "category": "live-chat",
     "script_patterns": [r"app\.purechat\.com"],
     "iframe_patterns": [r"purechat\.com"],
     "api_call_patterns": [r"\bpcWidget\b"],
     "runtime_globals": ["pcWidget"],
     "dom_selectors": ["#purechat-container"]},

    {"vendor": "chatlio", "category": "live-chat",
     "script_patterns": [r"w\.chatlio\.com"],
     "iframe_patterns": [r"chatlio\.com"],
     "api_call_patterns": [r"\b_chatlio\b"],
     "runtime_globals": ["_chatlio"],
     "dom_selectors": ["#chatlio-widget", "chatlio-widget"]},

    {"vendor": "liveagent", "category": "live-chat",
     "script_patterns": [r"\.ladesk\.com"],
     "iframe_patterns": [r"ladesk\.com"],
     "api_call_patterns": [r"\bLiveAgent\.createButton\b", r"\bLiveAgentTracker\b"],
     "runtime_globals": ["LiveAgent"],
     "dom_selectors": ["#la-chat-button", ".la-chat-button"]},

    {"vendor": "chaport", "category": "live-chat",
     "script_patterns": [r"app\.chaport\.com"],
     "iframe_patterns": [r"chaport\.com"],
     "api_call_patterns": [r"window\.chaportConfig\b", r"window\.chaport\b"],
     "runtime_globals": ["chaport"],
     "dom_selectors": ["#chaport-container"]},

    {"vendor": "channel-io", "category": "live-chat",
     "script_patterns": [r"cdn\.channel\.io"],
     "iframe_patterns": [r"channel\.io"],
     "api_call_patterns": [r"\bChannelIO\b\(", r"\bChannelIOInitialized\b"],
     "runtime_globals": ["ChannelIO", "ChannelIOInitialized"],
     "dom_selectors": ["#ch-plugin", ".ch-plugin"]},

    {"vendor": "liveperson", "category": "live-chat",
     "script_patterns": [r"lpcdn\.lpsnmedia\.net", r"lptag\.liveperson\.net"],
     "iframe_patterns": [r"liveperson\.net", r"lpsnmedia\.net"],
     "api_call_patterns": [r"\blpTag\.\w", r"\blpMTagConfig\b"],
     "runtime_globals": ["lpTag", "lpMTagConfig"],
     "dom_selectors": ["#lpChat", ".lp_desktop"]},

    {"vendor": "userlike", "category": "live-chat",
     "script_patterns": [r"userlike-cdn-widgets\.s3-eu-west-1\.amazonaws\.com", r"userlike\.com/api/chat"],
     "iframe_patterns": [r"userlike\.com"],
     "api_call_patterns": [r"\buserlikeConfig\b"],
     "runtime_globals": ["userlikeConfig"],
     "dom_selectors": ["#userlike", ".userlike-widget"]},

    {"vendor": "comm100", "category": "live-chat",
     "script_patterns": [r"vue\.comm100\.com", r"vue-static\.comm100\.com", r"chatserver\.comm100\.com"],
     "iframe_patterns": [r"comm100\.com"],
     "api_call_patterns": [r"\bComm100API\b"],
     "runtime_globals": ["Comm100API"],
     "dom_selectors": ["#comm100-container"]},

    {"vendor": "livehelpnow", "category": "live-chat",
     "script_patterns": [r"lhn\.livehelpnow\.net"],
     "iframe_patterns": [r"livehelpnow\.net"],
     "api_call_patterns": [r"window\.LHN\b", r"\blhnJQuery\b"],
     "runtime_globals": ["LHN", "lhnJQuery"],
     "dom_selectors": ["#lhnhocwidget"]},

    # ---------- HELPDESK / CHAT-CAPABLE ----------
    {"vendor": "zendesk", "category": "helpdesk",
     "script_patterns": [r"static\.zdassets\.com", r"v2\.zopim\.com", r"zendesk\.com/embeddable"],
     "iframe_patterns": [r"zendesk\.com", r"zdassets\.com"],
     "api_call_patterns": [r"\bzESettings\b", r"window\.zE\b", r"\$zopim\.livechat\."],
     "runtime_globals": ["zE", "zESettings", "$zopim", "zEmbed"],
     "dom_selectors": ["#launcher", "#webWidget", 'iframe[title*="Zendesk" i]']},

    {"vendor": "freshchat", "category": "helpdesk",
     "script_patterns": [r"wchat\.freshchat\.com", r"fw-cdn\.com"],
     "iframe_patterns": [r"freshchat\.com"],
     "api_call_patterns": [r"\bfcWidget\b"],
     "runtime_globals": ["fcWidget", "freshchat"],
     "dom_selectors": ["#fc_frame", "#freshworks-container"]},

    {"vendor": "freshworks-widget", "category": "helpdesk",
     "script_patterns": [r"widget\.freshworks\.com", r"euc-widget\.freshworks\.com"],
     "iframe_patterns": [r"freshworks\.com"],
     "api_call_patterns": [r"\bFreshworksWidget\b", r"\bfwSettings\b"],
     "runtime_globals": ["FreshworksWidget", "fwSettings"],
     "dom_selectors": ["#freshworks-container"]},

    {"vendor": "gorgias", "category": "helpdesk",
     "script_patterns": [r"config\.gorgias\.chat", r"client-uploads\.gorgias"],
     "iframe_patterns": [r"gorgias\.chat"],
     "api_call_patterns": [r"\bGorgiasChat\b"],
     "runtime_globals": ["GorgiasChat"],
     "dom_selectors": ["#gorgias-chat-container", "#gorgias-web-messenger-container"]},

    {"vendor": "helpscout", "category": "helpdesk",
     "script_patterns": [r"beacon-v2\.helpscout\.net", r"js\.hs-beacon\.com"],
     "iframe_patterns": [r"helpscout\.net"],
     "api_call_patterns": [r"window\.Beacon\b", r"Beacon\(\s*['\"]init['\"]"],
     "runtime_globals": ["Beacon"],
     "dom_selectors": [".BeaconContainer", "#beacon-container"]},

    {"vendor": "reamaze", "category": "helpdesk",
     "script_patterns": [r"cdn\.reamaze\.com"],
     "iframe_patterns": [r"reamaze\.com", r"reamaze\.io"],
     "api_call_patterns": [r"window\._support\s*=", r"\breamaze\b\.\w"],
     "runtime_globals": ["_support", "reamaze"],
     "dom_selectors": ["#reamaze-widget"]},

    {"vendor": "kustomer", "category": "helpdesk",
     "script_patterns": [r"cdn\.kustomerapp\.com"],
     "iframe_patterns": [r"kustomerapp\.com"],
     "api_call_patterns": [r"\bKustomer\.start\b"],
     "runtime_globals": ["Kustomer"],
     "dom_selectors": ["#kustomer-ui-sdk-iframe"]},

    {"vendor": "gladly", "category": "helpdesk",
     "script_patterns": [r"cdn\.gladly\.com"],
     "iframe_patterns": [r"gladly\.com"],
     "api_call_patterns": [r"\bgladlyConfig\b", r"window\.Gladly\b"],
     "runtime_globals": ["Gladly", "gladlyConfig"],
     "dom_selectors": ["#gladly-chat"]},

    {"vendor": "front", "category": "helpdesk",
     "script_patterns": [r"chat-assets\.frontapp\.com"],
     "iframe_patterns": [r"frontapp\.com"],
     "api_call_patterns": [r"\bFrontChat\b"],
     "runtime_globals": ["FrontChat"],
     "dom_selectors": ["#front-chat-container", "#front-chat-iframe"]},

    {"vendor": "helpcrunch", "category": "helpdesk",
     "script_patterns": [r"cdn\.helpcrunch\.com"],
     "iframe_patterns": [r"helpcrunch\.com"],
     "api_call_patterns": [r"\bHelpCrunch\b\("],
     "runtime_globals": ["HelpCrunch"],
     "dom_selectors": ["#helpcrunch-container"]},

    {"vendor": "hubspot-chat", "category": "helpdesk",
     "script_patterns": [r"js\.hs-scripts\.com"],
     "iframe_patterns": [r"app\.hubspot\.com.*conversations"],
     "api_call_patterns": [r"\bhsConversationsSettings\b", r"\bHubSpotConversations\b"],
     "runtime_globals": ["HubSpotConversations", "hsConversationsSettings"],
     "dom_selectors": ["#hubspot-messages-iframe-container"]},

    # ---------- ECOMMERCE-NATIVE ----------
    {"vendor": "shopify-inbox", "category": "ecommerce-chat",
     "script_patterns": [r"shopify-chat\.shopifyapps\.com", r"messaging-api\.shopifyapps\.com"],
     "iframe_patterns": [r"shopifyapps\.com.*chat"],
     "api_call_patterns": [r"\bShopifyChat\b\s*[.=(]"],
     "runtime_globals": ["ShopifyChat"],
     "dom_selectors": ["#shopify-chat", "shopify-chat"]},

    {"vendor": "shopify-ai-chat", "category": "ecommerce-chat",
     "script_patterns": [r"shopify-chat-agent.*\.fly\.dev", r"shop\.app/.*chat"],
     "iframe_patterns": [],
     "api_call_patterns": [r"\bshop-ai-chat\b"],
     "runtime_globals": [],
     "dom_selectors": [".shop-ai-chat-container", ".shop-ai-chat-bubble"]},

    {"vendor": "richpanel", "category": "ecommerce-chat",
     "script_patterns": [r"app\.richpanel\.com", r"cdn\.richpanel\.com"],
     "iframe_patterns": [r"richpanel\.com"],
     "api_call_patterns": [r"window\.richpanel\b", r"\bRichpanel\.\w"],
     "runtime_globals": ["richpanel", "Richpanel"],
     "dom_selectors": ["#richpanel-container"]},

    {"vendor": "delightchat", "category": "ecommerce-chat",
     "script_patterns": [r"cdn\.delightchat\.io", r"app\.delightchat\.io"],
     "iframe_patterns": [r"delightchat\.io"],
     "api_call_patterns": [r"\bDelightChat\b"],
     "runtime_globals": ["DelightChat"],
     "dom_selectors": [".delightchat-widget"]},

    {"vendor": "zipchat", "category": "ecommerce-chat",
     "script_patterns": [r"cdn\.zipchat\.ai", r"widget\.zipchat\.ai"],
     "iframe_patterns": [r"zipchat\.ai"],
     "api_call_patterns": [r"window\.zipchat\b"],
     "runtime_globals": ["zipchat"],
     "dom_selectors": ["#zipchat-widget"]},

    {"vendor": "gohighlevel", "category": "ecommerce-chat",
     "script_patterns": [r"widgets\.leadconnectorhq\.com"],
     "iframe_patterns": [r"leadconnectorhq\.com"],
     "api_call_patterns": [r"\bleadConnector\b"],
     "runtime_globals": ["leadConnector"],
     "dom_selectors": ["chat-widget[location-id]", "chat-widget"]},

    # ---------- AI-NATIVE ----------
    {"vendor": "ada", "category": "ai-chat",
     "script_patterns": [r"static\.ada\.support"],
     "iframe_patterns": [r"ada\.support"],
     "api_call_patterns": [r"\badaEmbed\b", r"\badaSettings\b"],
     "runtime_globals": ["adaEmbed", "adaSettings"],
     "dom_selectors": ["#ada-chat-frame", "#ada-button-frame"]},

    {"vendor": "chatbase", "category": "ai-chat",
     "script_patterns": [r"chatbase\.co/embed"],
     "iframe_patterns": [r"chatbase\.co"],
     "api_call_patterns": [r"\bembeddedChatbotConfig\b"],
     "runtime_globals": ["embeddedChatbotConfig", "chatbase"],
     "dom_selectors": ["#chatbase-bubble"]},

    {"vendor": "voiceflow", "category": "ai-chat",
     "script_patterns": [r"cdn\.voiceflow\.com"],
     "iframe_patterns": [r"voiceflow\.com"],
     "api_call_patterns": [r"\bvoiceflow\.chat\.load\b", r"window\.voiceflow\b"],
     "runtime_globals": ["voiceflow"],
     "dom_selectors": ["#voiceflow-chat", ".vfrc-widget"]},

    {"vendor": "landbot", "category": "ai-chat",
     "script_patterns": [r"cdn\.landbot\.io", r"static\.landbot\.io"],
     "iframe_patterns": [r"landbot\.io"],
     "api_call_patterns": [r"\bnew\s+Landbot\.", r"\bmyLandbot\b"],
     "runtime_globals": ["Landbot", "myLandbot"],
     "dom_selectors": ["#landbot-widget", ".LandbotLivechat"]},

    {"vendor": "typebot", "category": "ai-chat",
     "script_patterns": [r"cdn\.typebot\.io", r"typebot\.io/embed"],
     "iframe_patterns": [r"typebot\.io"],
     "api_call_patterns": [r"\bTypebot\.initBubble\b", r"\bTypebot\.initStandard\b"],
     "runtime_globals": ["Typebot"],
     "dom_selectors": ["#typebot-bubble", "typebot-bubble"]},

    {"vendor": "botpress", "category": "ai-chat",
     "script_patterns": [r"cdn\.botpress\.cloud", r"mediafiles\.botpress\.cloud"],
     "iframe_patterns": [r"botpress\.cloud"],
     "api_call_patterns": [r"\bbotpressWebChat\b"],
     "runtime_globals": ["botpressWebChat", "botpress"],
     "dom_selectors": ["#bp-web-widget", "#bp-widget"]},

    {"vendor": "dialogflow", "category": "ai-chat",
     "script_patterns": [r"dialogflow\.cloud\.google\.com"],
     "iframe_patterns": [r"dialogflow\.cloud\.google\.com"],
     "api_call_patterns": [r"<df-messenger\b"],
     "runtime_globals": ["dfMessenger"],
     "dom_selectors": ["df-messenger"]},

    {"vendor": "yellow-ai", "category": "ai-chat",
     "script_patterns": [r"cdn\.yellowmessenger\.com", r"cdn\.yellow\.ai"],
     "iframe_patterns": [r"yellow\.ai", r"yellowmessenger\.com"],
     "api_call_patterns": [r"\bymConfig\b", r"\bYellowMessenger\b"],
     "runtime_globals": ["ymConfig", "YellowMessenger"],
     "dom_selectors": ["#ymDivBar"]},

    {"vendor": "haptik", "category": "ai-chat",
     "script_patterns": [r"haptik-web-sdk", r"toolassets\.haptikapi\.com"],
     "iframe_patterns": [r"haptik\.ai"],
     "api_call_patterns": [r"\bHaptikSDK\b", r"\bhaptikInit\b"],
     "runtime_globals": ["HaptikSDK", "haptikInit"],
     "dom_selectors": ["#haptik-xdk"]},

    {"vendor": "forethought", "category": "ai-chat",
     "script_patterns": [r"solve-widget\.forethought\.ai", r"cdn\.forethought\.ai"],
     "iframe_patterns": [r"forethought\.ai"],
     "api_call_patterns": [r"\bForethought\b\("],
     "runtime_globals": ["Forethought"],
     "dom_selectors": ["#forethought-chat"]},

    {"vendor": "wonderchat", "category": "ai-chat",
     "script_patterns": [r"cdn\.wonderchat\.io", r"app\.wonderchat\.io/scripts"],
     "iframe_patterns": [r"wonderchat\.io"],
     "api_call_patterns": [r"\bwonderchatConfig\b"],
     "runtime_globals": ["wonderchatConfig"],
     "dom_selectors": []},

    {"vendor": "chatling", "category": "ai-chat",
     "script_patterns": [r"chatling\.ai/embed"],
     "iframe_patterns": [r"chatling\.ai"],
     "api_call_patterns": [r"\bchtlConfig\b"],
     "runtime_globals": ["chtlConfig"],
     "dom_selectors": ["#chatling-widget"]},

    {"vendor": "sitegpt", "category": "ai-chat",
     "script_patterns": [r"cdn\.sitegpt\.ai", r"app\.sitegpt\.ai/widget"],
     "iframe_patterns": [r"sitegpt\.ai"],
     "api_call_patterns": [r"\bSiteGPT\b"],
     "runtime_globals": ["SiteGPT"],
     "dom_selectors": []},

    {"vendor": "docsbot", "category": "ai-chat",
     "script_patterns": [r"widget\.docsbot\.ai"],
     "iframe_patterns": [r"docsbot\.ai"],
     "api_call_patterns": [r"\bDocsBotAI\b"],
     "runtime_globals": ["DocsBotAI"],
     "dom_selectors": ["#docsbot-widget"]},

    {"vendor": "customgpt", "category": "ai-chat",
     "script_patterns": [r"cdn\.customgpt\.ai"],
     "iframe_patterns": [r"customgpt\.ai"],
     "api_call_patterns": [r"\bCustomGPT\b"],
     "runtime_globals": ["CustomGPT"],
     "dom_selectors": []},

    {"vendor": "hoory", "category": "ai-chat",
     "script_patterns": [r"app\.hoory\.com"],
     "iframe_patterns": [r"hoory\.com"],
     "api_call_patterns": [r"\bhoorySettings\b", r"window\.\$hoory\b"],
     "runtime_globals": ["$hoory", "hoorySettings"],
     "dom_selectors": ["#hoory-widget"]},

    # ---------- SAAS-NATIVE / B2B SUPPORT ----------
    {"vendor": "pylon", "category": "helpdesk",
     "script_patterns": [r"widget\.usepylon\.com", r"chat-app\.usepylon\.com"],
     "iframe_patterns": [r"usepylon\.com"],
     "api_call_patterns": [r"window\.Pylon\b", r"\bpylon-chat-widget\b"],
     "runtime_globals": ["Pylon"],
     "dom_selectors": ["#pylon-chat-frame", "[id^='pylon-']"]},

    {"vendor": "plain", "category": "helpdesk",
     "script_patterns": [r"chat-cdn\.plain\.com", r"chat\.cdn-plain\.com"],
     "iframe_patterns": [r"plain\.com.*chat"],
     "api_call_patterns": [r"window\.Plain\b\.", r"\bPlain\.init\("],
     "runtime_globals": ["Plain"],
     "dom_selectors": ["#plain-chat-container", "[data-plain-chat]"]},

    {"vendor": "zoho-salesiq", "category": "live-chat",
     "script_patterns": [r"salesiq\.zoho\.com/widget", r"salesiq\.zohopublic\.com", r"salesiq\.zoho\.\w+/widget"],
     "iframe_patterns": [r"salesiq\.zoho\.com", r"salesiq\.zohopublic\.com"],
     "api_call_patterns": [r"\$zoho\.salesiq", r"\bsiqembedid\b"],
     "runtime_globals": ["$zoho"],
     "dom_selectors": ["#zsiq_float", "#zsiqwidget", "#zsiq_agtpic"]},

    {"vendor": "kommunicate", "category": "ai-chat",
     "script_patterns": [r"cdn\.kommunicate\.io"],
     "iframe_patterns": [r"kommunicate\.io"],
     "api_call_patterns": [r"\bkommunicateSettings\b", r"window\.Kommunicate\b"],
     "runtime_globals": ["Kommunicate", "kommunicateSettings"],
     "dom_selectors": ["#kommunicate-widget-iframe", "#mck-sidebox-launcher"]},

    # ---------- OPEN SOURCE ----------
    {"vendor": "chatwoot", "category": "open-source-chat",
     "script_patterns": [r"app\.chatwoot\.com/packs/js/sdk", r"chatwoot\.com.*sdk"],
     "iframe_patterns": [r"chatwoot\.com"],
     "api_call_patterns": [r"\bchatwootSettings\b", r"\bchatwootSDK\.\w"],
     "runtime_globals": ["chatwootSettings", "$chatwoot", "chatwootSDK"],
     "dom_selectors": [".woot-widget-holder", "#chatwoot-widget"]},

    {"vendor": "rocket-chat", "category": "open-source-chat",
     "script_patterns": [r"livechat\.rocket\.chat"],
     "iframe_patterns": [r"rocket\.chat/livechat"],
     "api_call_patterns": [r"\bRocketChat\.livechat\."],
     "runtime_globals": ["RocketChat"],
     "dom_selectors": [".rocketchat-widget", "#rocketchat-iframe"]},

    {"vendor": "tiledesk", "category": "open-source-chat",
     "script_patterns": [r"widget\.tiledesk\.com"],
     "iframe_patterns": [r"tiledesk\.com"],
     "api_call_patterns": [r"\btiledeskSettings\b", r"window\.tiledesk\b"],
     "runtime_globals": ["tiledesk"],
     "dom_selectors": ["#tiledesk-container"]},
]


def compile_patterns():
    """Pre-compile all regexes once for speed."""
    for v in VENDORS:
        v["_script_re"] = [re.compile(p, re.IGNORECASE) for p in v["script_patterns"]]
        v["_iframe_re"] = [re.compile(p, re.IGNORECASE) for p in v["iframe_patterns"]]
        v["_api_re"] = [re.compile(p, re.IGNORECASE) for p in v["api_call_patterns"]]
    return VENDORS


def match_html(html: str):
    """Return list of vendor matches found in raw HTML.

    Only checks high-precision signals: script src URLs, iframe src URLs,
    and very specific JS API names. Class/id substring matching is intentionally
    excluded from Layer 1 because it produces false positives like sendBeacon
    matching helpscout's "Beacon" class pattern.
    """
    if not html:
        return []
    out = []
    seen = set()
    for v in VENDORS:
        if v["vendor"] in seen:
            continue
        for r in v.get("_script_re", []):
            if r.search(html):
                out.append({"vendor": v["vendor"], "category": v["category"], "signal": f"script:{r.pattern}"})
                seen.add(v["vendor"])
                break
        if v["vendor"] in seen:
            continue
        for r in v.get("_iframe_re", []):
            if r.search(html):
                out.append({"vendor": v["vendor"], "category": v["category"], "signal": f"iframe:{r.pattern}"})
                seen.add(v["vendor"])
                break
        if v["vendor"] in seen:
            continue
        for r in v.get("_api_re", []):
            if r.search(html):
                out.append({"vendor": v["vendor"], "category": v["category"], "signal": f"api:{r.pattern}"})
                seen.add(v["vendor"])
                break
    return out


if __name__ == "__main__":
    compile_patterns()
    print(f"Loaded {len(VENDORS)} vendor signatures (Layer 1 high-precision rules)")
