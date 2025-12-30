import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# -------------------------------------------------
# 1. 通用代理列表 (hyproxy.list)
# 剔除了：Google, TG, YouTube, Netflix, Disney, Spotify, 新闻, 社交
# 保留了：GitHub, Wiki, Reddit, Pinterest, Tumblr, AI
# -------------------------------------------------
PROXY_MAP = {
    'GitHub': 'GitHub',
    'Wikipedia': 'Wikipedia',
    'Reddit': 'Reddit',
    'Pinterest': 'Pinterest',
    'Tumblr': 'Tumblr',
    'Claude': 'Claude',
    'Gemini': 'Gemini',
    'Civitai': 'Civitai',      # AI绘画模型站，通常需要
    'HuggingFace': 'HuggingFace'
}

# -------------------------------------------------
# 2. H站/成人列表 (hyhk.list) -> 建议走 🇭🇰
# 包含 BM7 的规则 + 手动精选域名
# -------------------------------------------------
HK_MAP = {
    'Pornhub': 'Pornhub',
    'DMM': 'DMM',
    'Pixiv': 'Pixiv',          # P站，通常归类到二次元/H
}

# 手动补充的 H 站域名 (纯净版，无广告域名)
HK_MANUAL_DOMAINS = [
    # === 核心 AV 站 ===
    "xvideos.com", "xvideos-cdn.com",
    "xhamster.com",
    "jable.tv",               
    "missav.com", "missav.live", "missav.ws", "missav.ai",
    "91porn.com", "91porny.com", "91porna.com", "91short.com",
    "t66y.com",               # 1024
    "avple.tv",
    "supjav.com",
    "njav.tv", "njav.com",
    "javmost.xyz", "javmost.com",
    "javday.tv", "javday.app",
    "madou.club",             
    "netflav.com", "netflav5.com",
    "cableav.tv",
    "thisav.com",
    "pigav.com",
    "hqporner.com",
    "beeg.com",
    "youporn.com",
    "redtube.com",
    "tube8.com",
    "eporner.com",
    "txh066.com", "txh067.com", # 糖心
    "h5ajcc.com",             # 爱酱
    "4hu.tv",                 # 四虎
    "sezse.com",              # 色中色
    "52av.one",

    # === 漫画/本子 ===
    "18comic.org", "18comic.vip", "jmcomic.mic", # 禁漫
    "wnacg.com", "wnacg.org",
    "e-hentai.org", "exhentai.org", "ehgt.org",
    "nhentai.net",
    "hitomi.la",
    "picacg.com",
    "hentai-foundry.com",
    "tsumino.com",
    "pururin.io",
    "hentaifox.com",
    "hentaiera.com",
    "manhuapica.com",

    # === 数据库/查询 ===
    "javbus.com", "javbus.in",
    "javdb.com",
    "javlibrary.com",
    "jav.land",
    "jav321.com",
    "javmenu.com",
    "minnanana.net",
]

BASE_URL = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def download_single_rule(item):
    """下载单个 BM7 规则"""
    rule_name = item[1] # item is (Remark, RuleName)
    url = BASE_URL.format(name=rule_name)
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return (rule_name, resp.text)
        return (rule_name, None)
    except:
        return (rule_name, None)

def process_rules(raw_text, strategy_name="proxy"):
    """清洗规则：只留域名，剔除 IP"""
    processed_rules = []
    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('#', ';', '//')) or ',' not in line:
            continue
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue
        
        rule_type = parts[0].upper()
        target = parts[1]
        
        # 只保留域名
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT"]:
            # strategy_name 这里只是个占位符，实际 QX 里由 tag 决定
            # 但为了格式完整，我们填入 proxy
            final_rule = f"{rule_type}, {target}, {strategy_name}" 
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def build_list(target_map, manual_domains, filename, title, strategy="proxy"):
    """通用构建函数"""
    print(f"🔨 正在构建 {filename} ...")
    unique_rules = {}
    
    # 1. 下载 BM7
    if target_map:
        tasks = list(target_map.items())
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_rule = {executor.submit(download_single_rule, item): item for item in tasks}
            for future in concurrent.futures.as_completed(future_to_rule):
                try:
                    name, content = future.result()
                    if content:
                        rules = process_rules(content, strategy)
                        for fp, rule in rules:
                            if fp not in unique_rules:
                                unique_rules[fp] = rule
                except:
                    pass

    # 2. 合并手动域名
    if manual_domains:
        print(f"   ➕ 添加手动域名 {len(manual_domains)} 条")
        for domain in manual_domains:
            domain = domain.strip()
            final_rule = f"HOST-SUFFIX, {domain}, {strategy}"
            fingerprint = f"host-suffix,{domain}".lower()
            if fingerprint not in unique_rules:
                unique_rules[fingerprint] = final_rule

    # 3. 排序写入
    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    if not sorted_rules:
        print(f"   ⚠️ 警告：{filename} 为空，跳过写入")
        return

    tz = pytz.timezone('Asia/Shanghai')
    现在 = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# {filename} ({title})",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: {strategy.upper()} (Pure Domain)",
        ""
    ]
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"   ✅ 生成成功: {filename} (包含 {len(sorted_rules)} 条)")

def main():
    start_time = time.time()
    
    # 构建 hyproxy.list (通用代理)
    build_list(PROXY_MAP, [], "hyproxy.list", "General Proxy", "proxy")
    
    # 构建 hyhk.list (H站/HK专用)
    build_list(HK_MAP, HK_MANUAL_DOMAINS, "hyhk.list", "H-Sites for HK", "proxy")

    duration = time.time() - start_time
    print(f"\n🎉 全部完成！耗时: {duration:.2f} 秒")

if __name__ == "__main__":
    main()
