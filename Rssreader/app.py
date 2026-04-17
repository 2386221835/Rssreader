# -*- coding: utf-8 -*-
import streamlit as st
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time

# ================== 在这里配置你的信息 ==================
# 在这里预置一些RSS源作为示例，你可以修改或添加
MY_FEEDS = {
    "知乎每日精选": "https://rsshub.app/zhihu/daily",
    "36氪": "https://www.36kr.com/feed",
    "少数派": "https://sspai.com/feed",
    # 在这里继续添加，格式 "名称": "RSS链接",
}
# ====================================================

# --- 辅助函数 ---
def clean_html(raw_html):
    """使用BeautifulSoup清理HTML标签，提取纯文本"""
    if not raw_html:
        return "暂无描述"
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    text = soup.get_text()
    # 清理多余的空白字符
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()[:300] + "..." if len(text) > 300 else text.strip()

def parse_feed(feed_url):
    """使用feedparser解析单个RSS源，并返回标准化的文章列表"""
    try:
        feed = feedparser.parse(feed_url)
        entries = []
        for entry in feed.entries[:10]:  # 每个源最多取10条最新文章
            # 统一文章发布时间
            pub_time = entry.get('published_parsed', entry.get('updated_parsed'))
            if pub_time:
                pub_date = datetime(*pub_time[:6]).strftime('%Y-%m-%d %H:%M')
            else:
                pub_date = "未知时间"
            
            # 清理HTML内容
            description = clean_html(entry.get('summary', entry.get('description', '')))
            
            entries.append({
                'title': entry.get('title', '无标题'),
                'link': entry.get('link', '#'),
                'published': pub_date,
                'summary': description,
                'source': feed.feed.get('title', '未知来源')
            })
        return entries
    except Exception as e:
        st.error(f"解析 {feed_url} 时出错: {e}")
        return []

# --- 初始化Session State ---
if "feeds" not in st.session_state:
    # 从预置的字典初始化session_state中的feeds列表
    st.session_state.feeds = [{"name": name, "url": url} for name, url in MY_FEEDS.items()]

# --- UI界面 ---
st.set_page_config(page_title="我的RSS阅读器", layout="wide")
st.title("📰 我的RSS阅读器")

# --- 侧边栏：管理订阅源 ---
with st.sidebar:
    st.header("➕ 管理订阅源")
    with st.form("add_feed_form"):
        new_name = st.text_input("源名称")
        new_url = st.text_input("RSS链接")
        submitted = st.form_submit_button("添加订阅")
        if submitted and new_name and new_url:
            st.session_state.feeds.append({"name": new_name, "url": new_url})
            st.success(f"已添加订阅: {new_name}")
            time.sleep(0.5)
            st.rerun()
    
    st.header("📋 我的订阅列表")
    for i, feed in enumerate(st.session_state.feeds):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{feed['name']}**")
        with col2:
            if st.button("🗑️ 删除", key=f"del_{i}"):
                st.session_state.feeds.pop(i)
                st.rerun()
    
    st.markdown("---")
    if st.button("🔄 刷新所有订阅"):
        st.cache_data.clear()
        st.rerun()

# --- 主区域：展示文章 ---
# 使用缓存装饰器，避免频繁请求RSS源
@st.cache_data(ttl=1800)  # 缓存30分钟
def fetch_all_articles(feeds_list):
    """获取所有订阅源的文章"""
    all_articles = []
    for feed in feeds_list:
        articles = parse_feed(feed['url'])
        for article in articles:
            article['feed_name'] = feed['name']
        all_articles.extend(articles)
        # 避免请求过快
        time.sleep(0.5)
    # 按发布时间倒序排序
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    return all_articles

articles = fetch_all_articles(st.session_state.feeds)

if not articles:
    st.info("👋 欢迎使用！请在左侧添加你的第一个RSS订阅源。")
else:
    st.header(f"📬 最新动态 (共 {len(articles)} 条)")
    
    # 使用卡片视图展示文章
    for article in articles:
        with st.container():
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                st.markdown(f"### [{article['title']}]({article['link']})")
                st.caption(f"来源：{article['feed_name']}  |  发布于：{article['published']}")
                st.write(article['summary'])
            with col2:
                st.write("")  # 占位，保持布局
            st.divider()