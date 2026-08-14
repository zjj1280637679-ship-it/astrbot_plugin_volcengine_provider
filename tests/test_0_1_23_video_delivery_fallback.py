from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities.dashboard_asset_bridge import (
    _adapt_index_file,
    _select_compatible_asset,
    transform_dashboard_javascript,
)
from astrbot_plugin_volcengine_provider.capabilities.model_fields import MODEL_FIELD_SCHEMA
from astrbot_plugin_volcengine_provider.capabilities.model_fields_bridge import (
    _inject_owned_model_fields,
)

ARK = "volcengine_ark_chat_completion"
PLAN = "volcengine_agent_plan_chat_completion"
PLUGIN_KEYS = sorted(MODEL_FIELD_SCHEMA)


def _schema_payload() -> dict:
    return {
        "config_schema": {
            "provider": {
                "items": {
                    "modalities": {
                        "description": "模型能力",
                        "type": "list",
                        "options": ["text", "image", "audio", "tool_use"],
                        "labels": ["文本", "图像", "音频", "工具使用"],
                    },
                    "custom_extra_body": {"type": "dict"},
                }
            }
        },
        "provider_sources": [
            {"id": "ark", "type": ARK},
            {"id": "plan", "type": PLAN},
            {"id": "openai", "type": "openai_chat_completion"},
        ],
        "providers": [],
    }


def _dashboard_fixture(*, relaxed_minifier_shape: bool = False, labels_as_i18n_key: bool = False) -> str:
    plugin_rows = ",".join(
        f'{json.dumps(key)}:{{type:"string",invisible:true}}' for key in PLUGIN_KEYS
    )
    labels = (
        '"provider_group.provider.openai_chat_completion.modalities.labels"'
        if labels_as_i18n_key
        else '["文本","图像","音频","工具使用"]'
    )
    if relaxed_minifier_shape:
        boundary = '''$ === "googlegenai_chat_completion" && U.push( "custom_extra_body" )
; for ( const M of U ) { k.provider.items[M] && (k.provider.items[M].invisible = true); }'''
    else:
        boundary = '$==="googlegenai_chat_completion"&&U.push("custom_extra_body");for(const M of U)k.provider.items[M]&&(k.provider.items[M].invisible=!0);'

    return f'''global.document={{documentElement:{{lang:"zh-CN"}}}};
global.localStorage={{getItem:()=>"zh-CN"}};
const selected={{value:{{id:"ark",type:"{ARK}"}}}};
const base={{value:{{id:"base"}}}};
function me(x){{return false}}
function nt(C){{var Le,se;if(!base.value)return;const Q=((Le=selected.value)==null?void 0:Le.id)||base.value.id,q=`${{Q}}/${{C}}`,le=null;let re;re=["text","image","audio","tool_use"];let De=0;return{{id:q,enable:!0,provider_source_id:Q,model:C,modalities:re,custom_extra_body:{{}},max_context_tokens:De,reasoning:me(le)}}}}
function newCard(type){{selected.value={{id:type,type}};return nt("model")}}
function card(type){{
const l={{value:{{provider:{{items:{{modalities:{{options:["text","image","audio","tool_use"],labels:{labels}}},{plugin_rows},custom_extra_body:{{type:"dict"}}}}}}}}}};
const i={{value:{{type}}}};
const x=(()=>{{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];{boundary}return k}})();
return x.provider.items;
}}
console.log(JSON.stringify({{dialogs:{{ark:card("{ARK}"),plan:card("{PLAN}"),openai:card("openai_chat_completion"),xai:card("xai_chat_completion"),google:card("googlegenai_chat_completion")}},newCards:{{ark:newCard("{ARK}"),plan:newCard("{PLAN}"),openai:newCard("openai_chat_completion"),xai:newCard("xai_chat_completion")}}}}));'''


def _run_transformed(source: str) -> dict:
    transformed, status = transform_dashboard_javascript(source)
    assert status == 1
    completed = subprocess.run(
        ["node", "-e", transformed],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def main() -> None:
    service = SimpleNamespace(config={"provider_sources": [], "provider": []})
    schema = _inject_owned_model_fields(service, _schema_payload())
    items = schema["config_schema"]["provider"]["items"]
    for key in MODEL_FIELD_SCHEMA:
        assert items[key]["invisible"] is True

    result = _run_transformed(_dashboard_fixture())
    dialogs = result["dialogs"]
    for name in ("ark", "plan"):
        owned = dialogs[name]
        assert owned["modalities"]["options"] == ["text", "image", "audio", "tool_use", "video"]
        assert owned["modalities"]["labels"] == ["文本", "图像", "音频", "工具使用", "视频"]
        for key in PLUGIN_KEYS:
            assert owned[key]["invisible"] is False

    for name in ("openai", "xai", "google"):
        foreign = dialogs[name]
        assert foreign["modalities"]["options"] == ["text", "image", "audio", "tool_use"]
        assert foreign["modalities"]["labels"] == ["文本", "图像", "音频", "工具使用"]
        for key in PLUGIN_KEYS:
            assert foreign[key]["invisible"] is True

    new_cards = result["newCards"]
    for name in ("ark", "plan"):
        for key in PLUGIN_KEYS:
            assert key in new_cards[name], (name, key, new_cards[name])
    for name in ("openai", "xai"):
        for key in PLUGIN_KEYS:
            assert key not in new_cards[name], (name, key, new_cards[name])

    i18n = _run_transformed(_dashboard_fixture(labels_as_i18n_key=True))["dialogs"]
    assert i18n["ark"]["modalities"]["labels"] == ["文本", "图像", "音频", "工具使用", "视频"]
    assert isinstance(i18n["openai"]["modalities"]["labels"], str)

    relaxed = _run_transformed(_dashboard_fixture(relaxed_minifier_shape=True))
    assert relaxed["dialogs"]["ark"]["modalities"]["options"][-1] == "video"
    assert "video" not in relaxed["dialogs"]["openai"]["modalities"]["options"]

    # Destroy only the concrete new-card builder signature while leaving the
    # private schema-clone boundary intact.  A complete-asset status must become 0,
    # never remain 1 merely because one of the two required objects still matches.
    complete = _dashboard_fixture()
    assert "provider_source_id:Q" in complete
    dialog_only = complete.replace("provider_source_id:Q", "provider_source_x:Q", 1)
    untouched, half_status = transform_dashboard_javascript(dialog_only)
    assert half_status == 0
    assert untouched == dialog_only

    with tempfile.TemporaryDirectory(prefix="volcengine-0.1.24-object-scope-") as tmp:
        dist = Path(tmp) / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True)
        asset = assets / "provider-dialog.js"
        asset.write_text(_dashboard_fixture(), encoding="utf-8")
        index = dist / "index.html"
        index.write_text('<html><script type="module" src="/assets/provider-dialog.js"></script></html>', encoding="utf-8")
        selected = _select_compatible_asset(dist)
        assert selected == asset.resolve()
        adapted_index = _adapt_index_file(index, compatible_asset=selected)
        assert adapted_index != index.resolve()
        assert "provider-dialog.js?astrbot_volcengine=" in adapted_index.read_text(encoding="utf-8")
        assert "?astrbot_volcengine=" not in index.read_text(encoding="utf-8")

    print("OBJECT_SCOPED_MODEL_CARD_UI_0_1_24=OK")


if __name__ == "__main__":
    main()
