from __future__ import annotations


SCENE_HINT_TERMS: dict[str, list[str]] = {
    "login": ["登录", "login", "sign in"],
    "captcha": ["验证码", "captcha", "verification", "人机验证"],
    "account_security": ["账号安全", "account security", "密码", "手机验证"],
    "payment": ["支付", "付款", "payment", "checkout"],
    "recharge": ["充值", "recharge", "top up"],
    "purchase": ["购买", "订单", "purchase", "order", "buy"],
    "settings": ["设置", "settings"],
    "document": ["保存", "打开", "文件", "编辑", "document", "file"],
    "result_screen": ["胜利", "失败", "结算", "继续", "result", "victory", "defeat"],
    "death_screen": ["死亡", "复活", "重生", "death", "respawn"],
    "error_dialog": ["错误", "异常", "error", "failed"],
    "code_workspace": ["terminal", "console", "代码", "编辑器"],
}


class OcrSceneHintExtractor:
    def extract(self, text: str) -> list[str]:
        normalized = text.lower()
        hints: list[str] = []
        for scene, terms in SCENE_HINT_TERMS.items():
            if any(term.lower() in normalized for term in terms):
                hints.append(scene)
        return hints
