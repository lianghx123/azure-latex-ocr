# OCR to LaTeX

这是一个使用快捷键截图并通过 Azure OpenAI 接口进行 OCR 识别，将识别结果转为 LaTeX 代码的工具。识别结果将自动复制到剪贴板。

## 功能特性
- 快捷键截图选取区域
- 调用 Azure OpenAI 接口识别图片公式
- 将识别到的 LaTeX 代码复制到剪贴板
- 鼠标位置显示短暂提示

## 安装与运行
1. 克隆本项目：
   ```bash
   git clone https://github.com/yourusername/yourproject.git
   cd yourproject
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置 config.json：
   ```json
   {
      "hotkey": "ctrl+shift+a", // 默认快捷键
      "endpoint": "https://your_azure_service_endpoint/", // 例如https://****.openai.azure.com/
      "api_key": "your_api_key", // apikey
      "api_path": "your_api_path", // 例如openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview
      "api_config": {
         "messages": [
            {
            "role": "system",
            "content": [
               {
                  "type": "text",
                  "text": "你是一个latex公式的专家，请根据用户发送的latex公式图片，直接返回相应的latex代码" // 设定系统消息
               }
            ]
            },
            {
            "role": "user",
            "content": [
               {
                  "type": "text",
                  "text": "\n"
               },
               {
                  "type": "image_url",
                  "image_url": {
                  "url": "data:image/jpeg;base64,{encoded_image}" // encoded_image为截图替代的参数
                  }
               },
               {
                  "type": "text",
                  "text": "\n"
               }
            ]
            }
         ],
         "temperature": 0.7,
         "top_p": 0.95,
         "max_tokens": 800
      }
   }
   ```
4. 运行程序：
   ```bash
   python src/main.py
   ```