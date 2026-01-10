import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 1. 输出文件名
OUTPUT_FILENAME = "hyhk.list"

# 2. 策略名称 (User Request: Adult18)
STRATEGY_NAME = "Adult18"

# 3. BM7 规则列表 (保留原有的 H 站分类)
HK_MAP = {
    'Pornhub': 'Pornhub',
    'DMM': 'DMM',
    'Pixiv': 'Pixiv',
}

# 4. 新增外部规则源 (Repcz)
EXTRA_URLS = [
    "https://raw.githubusercontent.com/Repcz/Tool/71063f38ee984de2d3de3abc78137080089b2ed4/QuantumultX/Rules/Porn.list"
]

# 5. 手动补充的 H 站域名 (无广告纯净版)
HK_MANUAL_DOMAINS = [
    # === 核心 AV 站 ===
    "xvideos.com", "xvideos-cdn.com",
    "xhamster.com",
    "jable.tv",
    "missav.com", "missav.live", "missav.ws", "missav.ai",
    "91porn.com", "91porny.com", "91porna.com", "91short.com",
    "t66y.com",
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
    "txh066.com", "txh067.com",
    "h5ajcc.com",
    "4hu.tv",
    "sezse.com",
    "52av.one",

    # === 漫画/本子 ===
    "18comic.org", "18comic.vip", "jmcomic.mic",
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

# BM7 基础 URL
BM7_BASE_URL = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def fetch_url(url):
    """通用下载函数"""
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
        return None
    except Exception as e:
        print(f"   ❌ 下载失败: {url} -> {e}")
        return None

def download_bm7_rule(item):
    """下载单个 BM7 规则适配器"""
    rule_name = item[1]
    url = BM7_BASE_URL.format(name=rule_name)
    content = fetch_url(url)
    return (rule_name, content)

def process_rules(raw_text, strategy_name):
    """清洗规则：解析标准 QX 格式并重写策略"""
    processed_rules = []
    if not raw_text:
        return processed_rules
        
    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith(('#', ';', '//')) or ',' not in line:
            continue
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue
        
        # 提取关键部分
        rule_type = parts[0].upper()
        target = parts[1]
        
        # 仅处理域名相关规则
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT"]:
            # 强制使用指定策略 (Adult18)
            final_rule = f"{rule_type}, {target}, {strategy_name}" 
            # 生成指纹用于去重 (类型+域名，忽略大小写)
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def build_list():
    print(f"🔨 正在构建 {OUTPUT_FILENAME} (策略: {STRATEGY_NAME}) ...")
    unique_rules = {}
    
    # 1. 下载 BM7 规则 (并发)
    if HK_MAP:
        print("   ⬇️  正在下载 BM7 规则组...")
        tasks = list(HK_MAP.items())
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_rule = {executor.submit(download_bm7_rule, item): item for item in tasks}
            for future in concurrent.futures.as_completed(future_to_rule):
                name, content = future.result()
                if content:
                    rules = process_rules(content, STRATEGY_NAME)
                    for fp, rule in rules:
                        if fp not in unique_rules:
                            unique_rules[fp] = rule

    # 2. 下载额外规则 (Repcz 等)
    if EXTRA_URLS:
        print(f"   ⬇️  正在下载额外规则源 ({len(EXTRA_URLS)} 个)...")
        for url in EXTRA_URLS:
            content = fetch_url(url)
            if content:
                rules = process_rules(content, STRATEGY_NAME)
                print(f"       - 获取到 {len(rules)} 条规则")
                for fp, rule in rules:
                    if fp not in unique_rules:
                        unique_rules[fp] = rule

    # 3. 合并手动域名
    if HK_MANUAL_DOMAINS:
        print(f"   ➕ 添加手动域名 {len(HK_MANUAL_DOMAINS)} 条")
        for domain in HK_MANUAL_DOMAINS:
            domain = domain.strip()
            if not domain: continue
            # 手动列表默认为 HOST-SUFFIX
            final_rule = f"HOST-SUFFIX, {domain}, {STRATEGY_NAME}"
            fingerprint = f"host-suffix,{domain}".lower()
            if fingerprint not in unique_rules:
                unique_rules[fingerprint] = final_rule

    # 4. 排序写入
    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    if not sorted_rules:
        print(f"   ⚠️ 警告：结果为空，跳过写入")
        return

    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# {OUTPUT_FILENAME} (Adult Content Combined)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: {STRATEGY_NAME}",
        f"# 包含源: Blackmatrix7, Repcz, Manual",
        ""
    ]
    
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"   ✅ 生成成功: {OUTPUT_FILENAME} (包含 {len(sorted_rules)} 条)")

def main():
    start_time = time.time()
    build_list()
    duration = time.time() - start_time
    print(f"\n🎉 全部完成！耗时: {duration:.2f} 秒")

if __name__ == "__main__":
    main()
