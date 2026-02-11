pipeline {
  agent any
  
  stages {
    stage('检出') {
      steps {
        checkout scm
      }
    }
    
    stage('环境准备') {
      steps {
        sh 'python3 -m venv venv'
        sh '. venv/bin/activate && pip install -r requirements.txt'
        sh '. venv/bin/activate && playwright install chromium'
      }
    }
    
    stage('数据采集') {
      environment {
        // 请在 CODING/Gitee 项目设置 -> 变量/凭据 中配置这些 ID
        OPENAI_API_KEY = credentials('OPENAI_API_KEY')
        WEBHOOK_URL = credentials('WEBHOOK_URL')
        PUSHPLUS_TOKEN = credentials('PUSHPLUS_TOKEN')
      }
      steps {
        sh '. venv/bin/activate && python main.py --now'
      }
    }
    
    stage('生成静态站数据') {
      steps {
        sh '. venv/bin/activate && python export_data.py'
      }
    }
    
    stage('部署静态网站') {
      steps {
        // CODING 提供了“静态网站托管”功能，可以使用其内置脚本或插件上传 docs 目录
        // 这里以通用 Git 提交回写为例，或者使用平台特定的“网站部署”插件
        
        sh '''
          git config user.name "CI Bot"
          git config user.email "ci@bot.com"
          git add docs/policies.json docs/stats.json
          git commit -m "Auto update data [skip ci]" || echo "No changes to commit"
          git push origin HEAD:main
        '''
      }
    }
  }
  
  triggers {
    cron('0 9 * * *') // 每天早上 9 点运行
  }
}
