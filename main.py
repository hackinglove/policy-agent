import argparse
import schedule
import time
import sys
from policy_agent.utils import load_config, load_sources, logger
from policy_agent.storage import Storage
from policy_agent.crawler import PolicyCrawler
from policy_agent.summarizer import Summarizer
from policy_agent.notifier import Notifier

def job():
    logger.info("开始执行每日抓取任务...")
    
    # 1. 加载配置
    config = load_config()
    sources = load_sources()
    if not config or not sources:
        logger.error("配置加载失败，任务终止")
        return

    # 2. 初始化模块
    storage = Storage()
    crawler = PolicyCrawler(config, sources, storage)
    summarizer = Summarizer(config)
    notifier = Notifier(config)

    # 3. 抓取 (返回 policy 对象列表)
    # 模拟测试时，可能希望忽略日期限制，这里可以在 config 增加 debug 选项
    # crawler 内部逻辑目前比较严格，需确保 sources.json 选择器准确
    new_policies = crawler.run()
    
    logger.info(f"本次运行共抓取到 {len(new_policies)} 条新政策")

    # 4. 生成摘要并保存
    processed_policies = []
    for p in new_policies:
        # 生成摘要
        summary = summarizer.generate_summary(p['content'])
        p['summary'] = summary
        
        # 保存到数据库
        if storage.save_policy(p):
            processed_policies.append(p)
    
    # 5. 推送
    notifier.send(processed_policies)
    logger.info("推送流程已执行")

    logger.info("任务执行完毕")

def main():
    parser = argparse.ArgumentParser(description="数字经济政策自动采集 Agent")
    parser.add_argument('--now', action='store_true', help='立即执行一次')
    parser.add_argument('--loop', action='store_true', help='开启定时循环模式')
    args = parser.parse_args()

    if args.now:
        job()
    
    if args.loop:
        config = load_config()
        schedule_time = config.get('schedule', {}).get('time', "09:00")
        
        logger.info(f"开启定时模式，将于每天 {schedule_time} 执行")
        schedule.every().day.at(schedule_time).do(job)
        
        # 启动时先打印一下心跳
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
