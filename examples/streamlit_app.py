"""
Streamlit Web界面
为Deep Search Agent提供友好的Web界面
"""

import os
import sys
import streamlit as st
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import DeepSearchAgent, Config


def main():
    """主函数"""
    st.set_page_config(
        page_title="Deep Search Agent",
        page_icon="🔍",
        layout="wide"
    )

    st.title("Deep Search Agent")
    st.markdown("基于OpenAI的无框架深度搜索AI代理")

    # 侧边栏配置
    with st.sidebar:
        st.header("配置")

        # API密钥配置
        st.subheader("API密钥")
        openai_key = st.text_input("OpenAI API Key", type="password", value="")
        tavily_key = st.text_input("Tavily API Key", type="password", value="")

        # 高级配置
        st.subheader("高级配置")
        max_reflections = st.slider("反思次数", 1, 5, 2)
        max_search_results = st.slider("搜索结果数", 1, 10, 3)
        max_content_length = st.number_input("最大内容长度", 1000, 50000, 20000)

        # 模型选择
        model_name = st.selectbox("OpenAI模型", ["gpt-4o-mini", "gpt-4o"])

    # 主界面
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("研究查询")
        query = st.text_area(
            "请输入您要研究的问题",
            placeholder="例如：2025年人工智能发展趋势",
            height=100
        )

        # 预设查询示例
        st.subheader("示例查询")
        example_queries = [
            "2025年人工智能发展趋势",
            "深度学习在医疗领域的应用",
            "区块链技术的最新发展",
            "可持续能源技术趋势",
            "量子计算的发展现状"
        ]

        selected_example = st.selectbox("选择示例查询", ["自定义"] + example_queries)
        if selected_example != "自定义":
            query = selected_example

    with col2:
        st.header("状态信息")
        if 'agent' in st.session_state and hasattr(st.session_state.agent, 'state'):
            progress = st.session_state.agent.get_progress_summary()
            st.metric("总段落数", progress['total_paragraphs'])
            st.metric("已完成", progress['completed_paragraphs'])
            st.progress(progress['progress_percentage'] / 100)
        else:
            st.info("尚未开始研究")

    # 执行按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        start_research = st.button("开始研究", type="primary", use_container_width=True)

    # 验证配置
    if start_research:
        if not query.strip():
            st.error("请输入研究查询")
            return

        if not openai_key:
            st.error("请提供OpenAI API Key")
            return

        if not tavily_key:
            st.error("请提供Tavily API Key")
            return

        # 创建配置
        config = Config(
            openai_api_key=openai_key,
            tavily_api_key=tavily_key,
            default_llm_provider="openai",
            openai_model=model_name,
            max_reflections=max_reflections,
            max_search_results=max_search_results,
            max_content_length=max_content_length,
            output_dir="streamlit_reports"
        )

        # 执行研究
        execute_research(query, config)


def execute_research(query: str, config: Config):
    """执行研究"""
    try:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 初始化Agent
        status_text.text("正在初始化Agent...")
        agent = DeepSearchAgent(config)
        st.session_state.agent = agent

        progress_bar.progress(10)

        # 生成报告结构
        status_text.text("正在生成报告结构...")
        agent._generate_report_structure(query)
        progress_bar.progress(20)

        # 处理段落
        total_paragraphs = len(agent.state.paragraphs)
        for i in range(total_paragraphs):
            status_text.text(f"正在处理段落 {i+1}/{total_paragraphs}: {agent.state.paragraphs[i].title}")

            # 初始搜索和总结
            agent._initial_search_and_summary(i)
            progress_value = 20 + (i + 0.5) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))

            # 反思循环
            agent._reflection_loop(i)
            agent.state.paragraphs[i].research.mark_completed()

            progress_value = 20 + (i + 1) / total_paragraphs * 60
            progress_bar.progress(int(progress_value))

        # 生成最终报告
        status_text.text("正在生成最终报告...")
        final_report = agent._generate_final_report()
        progress_bar.progress(90)

        # 保存报告
        status_text.text("正在保存报告...")
        agent._save_report(final_report)
        progress_bar.progress(100)

        status_text.text("研究完成！")

        # 显示结果
        display_results(agent, final_report)

    except Exception as e:
        st.error(f"研究过程中发生错误: {str(e)}")


def display_results(agent: DeepSearchAgent, final_report: str):
    """显示研究结果"""
    st.header("研究结果")

    # 结果标签页
    tab1, tab2, tab3 = st.tabs(["最终报告", "详细信息", "下载"])

    with tab1:
        st.markdown(final_report)

    with tab2:
        # 段落详情
        st.subheader("段落详情")
        for i, paragraph in enumerate(agent.state.paragraphs):
            with st.expander(f"段落 {i+1}: {paragraph.title}"):
                st.write("**预期内容:**", paragraph.content)
                st.write("**最终内容:**", paragraph.research.latest_summary[:300] + "..."
                        if len(paragraph.research.latest_summary) > 300
                        else paragraph.research.latest_summary)
                st.write("**搜索次数:**", paragraph.research.get_search_count())
                st.write("**反思次数:**", paragraph.research.reflection_iteration)

        # 搜索历史
        st.subheader("搜索历史")
        all_searches = []
        for paragraph in agent.state.paragraphs:
            all_searches.extend(paragraph.research.search_history)

        if all_searches:
            for i, search in enumerate(all_searches):
                with st.expander(f"搜索 {i+1}: {search.query}"):
                    st.write("**URL:**", search.url)
                    st.write("**标题:**", search.title)
                    st.write("**内容预览:**", search.content[:200] + "..." if len(search.content) > 200 else search.content)
                    if search.score:
                        st.write("**相关度评分:**", search.score)

    with tab3:
        # 下载选项
        st.subheader("下载报告")

        # Markdown下载
        st.download_button(
            label="下载Markdown报告",
            data=final_report,
            file_name=f"deep_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

        # JSON状态下载
        state_json = agent.state.to_json()
        st.download_button(
            label="下载状态文件",
            data=state_json,
            file_name=f"deep_search_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()
