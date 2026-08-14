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
    _VIDEO_LABEL_FALLBACK_MARKER,
    _select_compatible_asset,
    transform_dashboard_javascript,
)

HOST_VALUES = ["text", "image", "audio", "tool_use"]
HOST_LABELS = ["文本", "图像", "音频", "工具使用"]


def main() -> None:
    # A compatible asset must contain all three concrete frontend objects used by
    # the feature: the selected-Source private metadata clone, the concrete new
    # model-card data builder, and the host checkbox-label helper. None of these
    # objects is an acceptable substitute for either of the others.
    original = r'''global.localStorage={getItem:(key)=>key==="astrbot-locale"?"zh-CN":null};
function I(S){if(Array.isArray(S.labels))return S.labels;return null}
function _(S,k,$){const U=I(S);return U?U[k]:$}
const selected={value:{id:"ark",type:"volcengine_ark_chat_completion"}},base={value:{id:"base"}};
function me(x){return false}
function nt(C){var Le,se;if(!base.value)return;const Q=((Le=selected.value)==null?void 0:Le.id)||base.value.id,q=`${Q}/${C}`,le=null;let re;re=["text","image","audio","tool_use"];let De=0;return{id:q,enable:!0,provider_source_id:Q,model:C,modalities:re,custom_extra_body:{},max_context_tokens:De,reasoning:me(le)}}
function card(type){
const l={value:{provider:{items:{modalities:{options:["text","image","audio","tool_use"],labels:["文本","图像","音频","工具使用"]},volcengine_video_input_profile:{type:"string",invisible:true},volcengine_temperature:{type:"string",invisible:true},custom_extra_body:{type:"dict"}}}}};
const i={value:{type}};
const x=(()=>{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];$==="googlegenai_chat_completion"&&U.push("custom_extra_body");for(const M of U)k.provider.items[M]&&(k.provider.items[M].invisible=!0);return k})();
return x.provider.items;
}
function rendered(type){const items=card(type),meta=items.modalities;return meta.options.map((option,index)=>({value:option,label:_(meta,index,option)}))}
console.log(JSON.stringify({cards:{ark:card("volcengine_ark_chat_completion"),plan:card("volcengine_agent_plan_chat_completion"),openai:card("openai_chat_completion"),xai:card("xai_chat_completion"),google:card("googlegenai_chat_completion")},rendered:{ark:rendered("volcengine_ark_chat_completion"),plan:rendered("volcengine_agent_plan_chat_completion"),openai:rendered("openai_chat_completion"),xai:rendered("xai_chat_completion")}}));'''

    transformed, status = transform_dashboard_javascript(original)
    assert status == 1
    assert transformed.count(_PATCH_MARKER) == 1

    completed = subprocess.run(
        ["node", "-e", transformed],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)
    cards = result["cards"]
    rendered = result["rendered"]

    for name in ("ark", "plan"):
        owned = cards[name]
        assert owned["modalities"]["options"] == [*HOST_VALUES, "video"]
        assert owned["modalities"]["labels"] == HOST_LABELS
        assert owned["modalities"][_VIDEO_LABEL_FALLBACK_MARKER] is True
        assert [item["label"] for item in rendered[name]] == [*HOST_LABELS, "视频"]
        assert owned["volcengine_video_input_profile"]["invisible"] is False
        assert owned["volcengine_temperature"]["invisible"] is False

    for foreign_name in ("openai", "xai"):
        foreign = cards[foreign_name]
        assert foreign["modalities"]["options"] == HOST_VALUES
        assert foreign["modalities"]["labels"] == HOST_LABELS
        assert _VIDEO_LABEL_FALLBACK_MARKER not in foreign["modalities"]
        assert [item["label"] for item in rendered[foreign_name]] == HOST_LABELS
        assert foreign["volcengine_video_input_profile"]["invisible"] is True
        assert foreign["volcengine_temperature"]["invisible"] is True

    assert cards["google"]["custom_extra_body"]["invisible"] is True

    untouched, missing_status = transform_dashboard_javascript("console.log('future')")
    assert missing_status == 0
    assert untouched == "console.log('future')"

    ambiguous, duplicate_status = transform_dashboard_javascript(original + original)
    assert duplicate_status != 1
    assert ambiguous == original + original

    without_renderer = original.replace(
        "function _(S,k,$){const U=I(S);return U?U[k]:$}",
        "function _(S,k,$){return $}",
        1,
    )
    renderer_missing, renderer_status = transform_dashboard_javascript(without_renderer)
    assert renderer_status == 0
    assert renderer_missing == without_renderer

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
