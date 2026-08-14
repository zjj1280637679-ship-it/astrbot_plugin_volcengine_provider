from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities.dashboard_asset_bridge import (
    _adapt_index_file,
    _select_compatible_asset,
    transform_dashboard_javascript,
)
from astrbot_plugin_volcengine_provider.capabilities.video_modality_fallback import (
    VIDEO_MODALITY_FALLBACK_MARKER,
    inject_video_modality_fallback,
    strip_video_modality,
)


def _schema_payload(*, native_video: bool = False) -> dict:
    options = ["text", "image", "audio", "tool_use"]
    if native_video:
        options.append("video")
    return {
        "config_schema": {
            "provider": {
                "items": {
                    "modalities": {
                        "type": "list",
                        "render_type": "checkbox",
                        "options": options,
                        "labels": "provider.items.modalities.labels",
                    }
                }
            }
        }
    }


def _dashboard_fixture(*, with_fallback: bool) -> str:
    marker = (
        f",{json.dumps(VIDEO_MODALITY_FALLBACK_MARKER)}:true"
        if with_fallback
        else ""
    )
    options = (
        '["text","image","audio","tool_use","video"]'
        if with_fallback
        else '["text","image","audio","tool_use"]'
    )
    labels = (
        '["文本 / Text","图像 / Image","音频 / Audio","工具使用 / Tool use","视频 / Video"]'
        if with_fallback
        else '"provider.items.modalities.labels"'
    )
    return f'''function card(type){{
const l={{value:{{provider:{{items:{{modalities:{{options:{options},labels:{labels}{marker}}},volcengine_video_input_profile:{{type:"string"}},volcengine_temperature:{{type:"string"}},custom_extra_body:{{type:"dict"}}}}}}}}}};
const i={{value:{{type}}}};
const x=(()=>{{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];$==="googlegenai_chat_completion"&&U.push("custom_extra_body");for(const M of U)k.provider.items[M]&&(k.provider.items[M].invisible=!0);return k}})();
return x.provider.items;
}}
console.log(JSON.stringify({{ark:card("volcengine_ark_chat_completion"),plan:card("volcengine_agent_plan_chat_completion"),openai:card("openai_chat_completion"),google:card("googlegenai_chat_completion")}}));'''


def main() -> None:
    base = _schema_payload()
    before = copy.deepcopy(base)
    injected = inject_video_modality_fallback(base)
    assert base == before
    modalities = injected["config_schema"]["provider"]["items"]["modalities"]
    assert modalities["options"] == ["text", "image", "audio", "tool_use", "video"]
    assert modalities["labels"][-1] == "视频 / Video"
    assert modalities[VIDEO_MODALITY_FALLBACK_MARKER] is True

    reinjected = inject_video_modality_fallback(injected)
    re_modalities = reinjected["config_schema"]["provider"]["items"]["modalities"]
    assert re_modalities["options"].count("video") == 1
    assert re_modalities[VIDEO_MODALITY_FALLBACK_MARKER] is True

    native = inject_video_modality_fallback(_schema_payload(native_video=True))
    native_modalities = native["config_schema"]["provider"]["items"]["modalities"]
    assert native_modalities["options"].count("video") == 1
    assert native_modalities["labels"] == "provider.items.modalities.labels"
    assert VIDEO_MODALITY_FALLBACK_MARKER not in native_modalities

    foreign_card = {"modalities": ["text", "image", "video", "tool_use"]}
    assert strip_video_modality(foreign_card) is True
    assert foreign_card["modalities"] == ["text", "image", "tool_use"]
    assert strip_video_modality(foreign_card) is False

    transformed, matches = transform_dashboard_javascript(
        _dashboard_fixture(with_fallback=True)
    )
    assert matches == 1
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
        assert owned["modalities"]["labels"][-1] == "视频"
        assert VIDEO_MODALITY_FALLBACK_MARKER not in owned["modalities"]
    for foreign in (result["openai"], result["google"]):
        assert foreign["modalities"]["options"] == [
            "text",
            "image",
            "audio",
            "tool_use",
        ]
        assert "video" not in foreign["modalities"]["options"]
        assert VIDEO_MODALITY_FALLBACK_MARKER not in foreign["modalities"]

    # A clean host schema still behaves exactly like the 0.1.22 precise path.
    transformed_clean, clean_matches = transform_dashboard_javascript(
        _dashboard_fixture(with_fallback=False)
    )
    assert clean_matches == 1
    clean_completed = subprocess.run(
        ["node", "-e", transformed_clean],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    clean_result = json.loads(clean_completed.stdout)
    assert clean_result["ark"]["modalities"]["options"][-1] == "video"
    assert "video" not in clean_result["openai"]["modalities"]["options"]

    # The copied index points at the same host bundle path with a content-derived
    # query suffix. FastAPI routes by path, while the browser cache keys the full
    # URL, so an old cached bundle cannot satisfy this request.
    with tempfile.TemporaryDirectory(prefix="volcengine-0.1.23-delivery-") as tmp:
        dist = Path(tmp) / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True)
        asset = assets / "provider-dialog.js"
        asset.write_text(_dashboard_fixture(with_fallback=False), encoding="utf-8")
        index = dist / "index.html"
        index.write_text(
            '<html><script type="module" src="/assets/provider-dialog.js"></script></html>',
            encoding="utf-8",
        )
        selected = _select_compatible_asset(dist)
        assert selected == asset.resolve()
        adapted_index = _adapt_index_file(index, compatible_asset=selected)
        assert adapted_index != index.resolve()
        adapted_html = adapted_index.read_text(encoding="utf-8")
        assert "provider-dialog.js?astrbot_volcengine=" in adapted_html
        assert "?astrbot_volcengine=" not in index.read_text(encoding="utf-8")

    print("VIDEO_DELIVERY_FALLBACK_0_1_23=OK")


if __name__ == "__main__":
    main()
