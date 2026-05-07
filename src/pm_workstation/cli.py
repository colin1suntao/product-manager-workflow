"""CLI入口点"""

import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """产品经理多Agent协作工作站 - 智能需求解析、原型生成、文档编撰、校验纠错"""
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="服务器监听地址")
@click.option("--port", default=8000, help="服务器端口")
@click.option("--reload", is_flag=True, help="启用热重载（开发模式）")
def serve(host: str, port: int, reload: bool):
    """启动Web服务器"""
    import uvicorn

    uvicorn.run(
        "pm_workstation.api:app",
        host=host,
        port=port,
        reload=reload,
    )


@main.command()
@click.option("--model", default="openai", help="默认LLM模型 (openai/anthropic)")
@click.option("--api-key", help="LLM API密钥")
def configure(model: str, api_key: str):
    """配置系统设置"""
    from pm_workstation.config import settings

    if model:
        settings.default_model = model
    if api_key:
        settings.api_key = api_key

    settings.save()
    click.echo("配置已保存")


if __name__ == "__main__":
    main()
