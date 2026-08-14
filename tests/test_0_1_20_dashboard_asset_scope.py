from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities.dashboard_asset_bridge import (
    _PATCH_MARKER,
    _select_compatible_asset,
    transform_dashboard_javascript,
)


def main() -> None:
    # This fixture models the concrete AstrBot v4.27.x object that matters here:
    # the host-owned upper modalities metadata already contains four localized
    # Chinese labels.  The plugin is allowed to append one fifth Video label only
    # after the current dialog is known to belong to one of its two Source types;
    # it is not allowed to replace or bilingualize the four labels it did not own.
    original = r'''global.document={documentElement:{lang:"zh-CN"}};
global.localStorage={getItem:()=>"zh-CN"};
function card(type){
const l={value:{provider:{items:{modalities:{options:["text","image","audio","tool_use"],labels:["文本","图像","音频","工具使用"]},volcengine_video_input_profile:{type:"string",invisible:true},volcengine_temperature:{type:"string",invisible:true},custom_extra_body:{type:"dict"}}}}};
const i={value:{type}};
const x=(()=>{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];$==="googlegenai_chat_completion"&&U.push("custom_extra_body");for(const M of U)k.provider.items[M]&&(k.provider.items[M].invisible=!0);return k})();
return x.provider.items;
}
console.log(JSON.stringify({ark:card("volcengine_ark_chat_completion"),plan:card("volcengine_agent_plan_chat_completion"),openai:card("openai_chat_completion"),xai:card("xai_chat_completion"),google:card("googlegenai_chat_completion")}));'''

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

    # The concrete Ark / Agent Plan model-card private clone owns only the plugin
    # delta: one Video capability plus visibility of the lower Volcengine rows.
    # The four native host labels must remain exactly the four host labels.
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
        assert owned["volcengine_video_input_profile"]["invisible"] is False
        assert owned["volcengine_temperature"]["invisible"] is False

    # OpenAI and xAI are separate concrete foreign model-card objects even when a
    # user points either one at a Volcengine-compatible endpoint.  Neither their
    # native modalities options nor their native labels may be modified, and the
    # lower Volcengine request rows must stay hidden.
    for foreign_name in ("openai", "xai"):
        foreign = result[foreign_name]
        assert foreign["modalities"]["options"] == [
            "text",
            "image",
            "audio",
            "tool_use",
        ]
        assert foreign["modalities"]["labels"] == [
            "文本",
            "图像",
            "音频",
            "工具使用",
        ]
        assert foreign["volcengine_video_input_profile"]["invisible"] is True
        assert foreign["volcengine_temperature"]["invisible"] is True

    # Google's own host-specific hiding rule remains AstrBot's responsibility and
    # is preserved by the plugin transform rather than being reinterpreted as a
    # Volcengine rule.
    assert result["google"]["custom_extra_body"]["invisible"] is True

    untouched, missing_matches = transform_dashboard_javascript("console.log('future')")
    assert missing_matches == 0
    assert untouched == "console.log('future')"

    ambiguous, duplicate_matches = transform_dashboard_javascript(original + original)
    assert duplicate_matches == 2
    assert ambiguous == original + original

    # Asset discovery follows the runtime ``static_folder`` rather than assuming
    # whether AstrBot selected data/dist, its bundled dist, or a custom WebUI.
    with tempfile.TemporaryDirectory(prefix="volcengine-dashboard-scope-") as tmp:
        dist = Path(tmp) / "served-dist"
        assets = dist / "assets"
        assets.mkdir(parents=True)
        target = assets / "provider-dialog.js"
        target.write_text(original, encoding="utf-8")
        (assets / "unrelated.js").write_text("console.log('plain')", encoding="utf-8")
        assert _select_compatible_asset(dist) == target.resolve()

        ambiguous_dist = Path(tmp) / "ambiguous-dist"
        ambiguous_assets = ambiguous_dist / "assets"
        ambiguous_assets.mkdir(parents=True)
        (ambiguous_assets / "a.js").write_text(original, encoding="utf-8")
        (ambiguous_assets / "b.js").write_text(original, encoding="utf-8")
        assert _select_compatible_asset(ambiguous_dist) is None
    print("DASHBOARD_ASSET_SCOPE_0_1_20=OK")


if __name__ == "__main__":
    main()
