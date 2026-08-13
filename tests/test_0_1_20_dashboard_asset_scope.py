from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities.dashboard_asset_bridge import (
    _PATCH_MARKER,
    transform_dashboard_javascript,
)


def main() -> None:
    original = r'''function card(type){
const l={value:{provider:{items:{modalities:{options:["text","image","audio","tool_use"],labels:"provider.items.modalities.labels"},volcengine_video_input_profile:{type:"string"},volcengine_temperature:{type:"string"},custom_extra_body:{type:"dict"}}}}};
const i={value:{type}};
const x=(()=>{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];$==="googlegenai_chat_completion"&&U.push("custom_extra_body");for(const M of U)k.provider.items[M]&&(k.provider.items[M].invisible=!0);return k})();
return x.provider.items;
}
console.log(JSON.stringify({ark:card("volcengine_ark_chat_completion"),plan:card("volcengine_agent_plan_chat_completion"),openai:card("openai_chat_completion"),google:card("googlegenai_chat_completion")}));'''

    transformed, matches = transform_dashboard_javascript(original)
    assert matches == 1
    assert transformed.count(_PATCH_MARKER) == 1

    completed = subprocess.run(
        ["node", "-e", transformed],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)

    for owned in (result["ark"], result["plan"]):
        assert owned["modalities"]["options"] == [
            "text",
            "image",
            "audio",
            "tool_use",
            "video",
        ]
        assert owned["modalities"]["labels"] == [
            "文本",
            "图像",
            "音频",
            "工具使用",
            "视频",
        ]
        assert owned["volcengine_video_input_profile"].get("invisible") is not True
        assert owned["volcengine_temperature"].get("invisible") is not True

    assert result["openai"]["modalities"]["options"] == [
        "text",
        "image",
        "audio",
        "tool_use",
    ]
    assert result["openai"]["modalities"]["labels"] == "provider.items.modalities.labels"
    assert result["openai"]["volcengine_video_input_profile"]["invisible"] is True
    assert result["openai"]["volcengine_temperature"]["invisible"] is True
    assert result["google"]["custom_extra_body"]["invisible"] is True

    untouched, missing_matches = transform_dashboard_javascript("console.log('future')")
    assert missing_matches == 0
    assert untouched == "console.log('future')"

    ambiguous, duplicate_matches = transform_dashboard_javascript(original + original)
    assert duplicate_matches == 2
    assert ambiguous == original + original
    print("DASHBOARD_ASSET_SCOPE_0_1_20=OK")


if __name__ == "__main__":
    main()
