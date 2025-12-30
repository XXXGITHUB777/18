import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 核心策略：【直连拆包】
# 只包含核心App，去除了乱七八糟的全家桶
MY_APP_MAP = {
    # --- 社交 ---
    '微信': 'WeChat',
    'QQ': 'TencentQQ',
    '微博': 'Weibo',
    '新浪': 'Sina',
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # --- 支付与购物 ---
    '支付宝': 'AliPay',
    '淘宝': 'Taobao',
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',
    '饿了么': 'Eleme',

    # --- 视频 ---
    '抖音': 'DouYin',
    '快手': 'KuaiShou',
    '哔哩哔哩': 'BiliBili',
    # 蛋播依赖
    '斗鱼直播': 'Douyu',
    '虎牙直播': 'HuYa',
    'YY直播': 'YYeTs',

    # --- 出行 ---
    '高德地图': 'GaoDe',
    '滴滴出行': 'DiDi',
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng',
    '百度全家桶': 'Baidu',       

    # --- 系统/工具 ---
    'AppStore': 'AppStore',
    'iCloud': 'iCloud',
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',
    '美图系列': 'MeiTu',
    '迅飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',

    # --- 运营商 ---
    '中国电信': 'ChinaTelecom',
    '中国联通': 'ChinaUnicom'
}

BASE_URL = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def download_single_rule(item):
    remark, rule_name = item
    url = BASE_URL.format(name=rule_name)
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return (rule_name, resp.text)
        else:
            return (rule_name, None)
    except:
        return (rule_name, None)

def process_rules(raw_text):
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
        
        # 直连策略：只保留域名，强制 direct
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT"]:
            final_rule = f"{rule_type}, {target}, direct"
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动 Direct 直连规则构建...")
    start_time = time.time()
    
    unique_rules = {} 
    tasks = list(MY_APP_MAP.items())
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_rule = {executor.submit(download_single_rule, item): item for item in tasks}
        
        for future in concurrent.futures.as_completed(future_to_rule):
            try:
                name, content = future.result()
                if content:
                    rules_list = process_rules(content)
                    for fp, rule in rules_list:
                        if fp not in unique_rules:
                            unique_rules[fp] = rule
            except:
                pass

    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    duration = time.time() - start_time
    print(f"📊 直连规则总数: {len(sorted_rules)}")
    
    if not sorted_rules:
        exit(1)

    tz = pytz.timezone('Asia/Shanghai')
    现在 = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# hydirect.list (Ultra Lite)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: 强制 DIRECT (纯域名)",
        ""
    ]
    
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"✅ 生成成功: hydirect.list")

if __name__ == "__main__":
    main()
