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
    _VIDEO_LABEL_FALLBACK_MARKER,
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
HOST_VALUES = ["text", "image", "audio", "tool_use"]
HOST_ZH_LABELS = ["文本", "图像", "音频", "工具使用"]


def _schema_payload() -> dict:
    return {
        "config_schema": {
            "provider": {
                "items": {
                    "modalities": {
                        "description": "模型能力",
                        "type": "list",
                        "options": list(HOST_VALUES),
                        "labels": list(HOST_ZH_LABELS),
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


def _dashboard_fixture(
    *,
    relaxed_minifier_shape: bool = False,
    labels_as_i18n_key: bool = False,
    include_reasoning: bool = True,
) -> str:
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
    reasoning_member = ",reasoning:me(le)" if include_reasoning else ""

    # The helper pair models the concrete ConfigItemRenderer contract: I(S)
    # resolves host-owned metadata labels; _(S,index,option) chooses one label.
    # The plugin is allowed to change only the missing fifth Video fallback, not
    # the host translation source that produces indices zero through three.
    return f'''global.localStorage={{getItem:(key)=>key==="astrbot-locale"?"zh-CN":null}};
const selected={{value:{{id:"ark",type:"{ARK}"}}}};
const base={{value:{{id:"base"}}}};
function me(x){{return false}}
function I(S){{if(Array.isArray(S.labels))return S.labels;if(typeof S.labels==="string")return ["文本","图像","音频","工具使用"];return null}}
function _(S,k,$){{const U=I(S);return U?U[k]:$}}
function nt(C){{var Le,se;if(!base.value)return;const Q=((Le=selected.value)==null?void 0:Le.id)||base.value.id,q=`${{Q}}/${{C}}`,le={{limit:{{context:128000}}}};let re;re=["text","image","audio","tool_use"];let De=0;return(se=le==null?void 0:le.limit)!=null&&se.context&&typeof le.limit.context=="number"&&(De=le.limit.context),{{id:q,enable:!0,provider_source_id:Q,model:C,modalities:re,custom_extra_body:{{}},max_context_tokens:De{reasoning_member}}}}}
function newCard(type){{selected.value={{id:type,type}};return nt("model")}}
function card(type){{
const l={{value:{{provider:{{items:{{modalities:{{options:["text","image","audio","tool_use"],labels:{labels}}},{plugin_rows},custom_extra_body:{{type:"dict"}}}}}}}}}};
const i={{value:{{type}}}};
const x=(()=>{{var J,F,j;if(!((F=(J=l.value)==null?void 0:J.provider)!=null&&F.items))return l.value;const k=JSON.parse(JSON.stringify(l.value)),$=(j=i.value)==null?void 0:j.type,U=["id","model"];{boundary}return k}})();
return x.provider.items;
}}
function rendered(type){{const items=card(type),meta=items.modalities;return meta.options.map((option,index)=>({{value:option,label:_(meta,index,option)}}))}}
console.log(JSON.stringify({{dialogs:{{ark:card("{ARK}"),plan:card("{PLAN}"),openai:card("openai_chat_completion"),xai:card("xai_chat_completion"),google:card("googlegenai_chat_completion")}},rendered:{{ark:rendered("{ARK}"),plan:rendered("{PLAN}"),openai:rendered("openai_chat_completion"),xai:rendered("xai_chat_completion")}},newCards:{{ark:newCard("{ARK}"),plan:newCard("{PLAN}"),openai:newCard("openai_chat_completion"),xai:newCard("xai_chat_completion")}}}}));'''


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


def _pairs(items: list[dict[str, str]]) -> list[tuple[str, str]]:
    return [(str(item["value"]), str(item["label"])) for item in items]


def main() -> None:
    service = SimpleNamespace(config={"provider_sources": [], "provider": []})
    schema = _inject_owned_model_fields(service, _schema_payload())
    items = schema["config_schema"]["provider"]["items"]
    for key in MODEL_FIELD_SCHEMA:
        assert items[key]["invisible"] is True

    result = _run_transformed(_dashboard_fixture())
    dialogs = result["dialogs"]
    rendered = result["rendered"]

    for name in ("ark", "plan"):
        owned = dialogs[name]
        meta = owned["modalities"]
        assert meta["options"] == [*HOST_VALUES, "video"]
        # Metadata ownership is the important assertion: the plugin must not
        # replace or extend AstrBot's four host labels merely to name Video.
        assert meta["labels"] == HOST_ZH_LABELS
        assert meta[_VIDEO_LABEL_FALLBACK_MARKER] is True
        assert _pairs(rendered[name]) == [
            ("text", "文本"),
            ("image", "图像"),
            ("audio", "音频"),
            ("tool_use", "工具使用"),
            ("video", "视频"),
        ]
        for key in PLUGIN_KEYS:
            assert owned[key]["invisible"] is False

    for name in ("openai", "xai", "google"):
        foreign = dialogs[name]
        meta = foreign["modalities"]
        assert meta["options"] == HOST_VALUES
        assert meta["labels"] == HOST_ZH_LABELS
        assert _VIDEO_LABEL_FALLBACK_MARKER not in meta
        for key in PLUGIN_KEYS:
            assert foreign[key]["invisible"] is True

    for name in ("openai", "xai"):
        assert _pairs(rendered[name]) == list(zip(HOST_VALUES, HOST_ZH_LABELS))

    new_cards = result["newCards"]
    for name in ("ark", "plan"):
        for key in PLUGIN_KEYS:
            assert key in new_cards[name], (name, key, new_cards[name])
    for name in ("openai", "xai"):
        for key in PLUGIN_KEYS:
            assert key not in new_cards[name], (name, key, new_cards[name])

    # AstrBot 4.27.4 removed the provider-config ``reasoning`` member while
    # preserving the rest of this builder. The same object-scoped contract must
    # survive that host change without widening the foreign-provider surface.
    no_reasoning = _run_transformed(_dashboard_fixture(include_reasoning=False))
    for name in ("ark", "plan"):
        assert no_reasoning["dialogs"][name]["modalities"]["options"] == [
            *HOST_VALUES,
            "video",
        ]
        for key in PLUGIN_KEYS:
            assert key in no_reasoning["newCards"][name]
    for name in ("openai", "xai", "google"):
        assert no_reasoning["dialogs"][name]["modalities"]["options"] == HOST_VALUES
    for name in ("openai", "xai"):
        for key in PLUGIN_KEYS:
            assert key not in no_reasoning["newCards"][name]

    i18n_result = _run_transformed(_dashboard_fixture(labels_as_i18n_key=True))
    i18n_dialogs = i18n_result["dialogs"]
    i18n_rendered = i18n_result["rendered"]
    host_i18n_key = "provider_group.provider.openai_chat_completion.modalities.labels"
    # Both owned and foreign metadata keep the same host i18n key. Only the
    # renderer's owned Video overflow gets a plugin label.
    assert i18n_dialogs["ark"]["modalities"]["labels"] == host_i18n_key
    assert i18n_dialogs["openai"]["modalities"]["labels"] == host_i18n_key
    assert _pairs(i18n_rendered["ark"])[0:4] == list(zip(HOST_VALUES, HOST_ZH_LABELS))
    assert _pairs(i18n_rendered["ark"])[4] == ("video", "视频")
    assert _pairs(i18n_rendered["openai"]) == list(zip(HOST_VALUES, HOST_ZH_LABELS))

    relaxed = _run_transformed(_dashboard_fixture(relaxed_minifier_shape=True))
    assert _pairs(relaxed["rendered"]["ark"])[-1] == ("video", "视频")
    assert "video" not in [item["value"] for item in relaxed["rendered"]["openai"]]

    complete = _dashboard_fixture()
    assert "provider_source_id:Q" in complete
    dialog_only = complete.replace("provider_source_id:Q", "provider_source_x:Q", 1)
    untouched, half_status = transform_dashboard_javascript(dialog_only)
    assert half_status == 0
    assert untouched == dialog_only

    without_renderer = complete.replace(
        "function _(S,k,$){const U=I(S);return U?U[k]:$}",
        "function _(S,k,$){return $}",
        1,
    )
    untouched_renderer, renderer_status = transform_dashboard_javascript(without_renderer)
    assert renderer_status == 0
    assert untouched_renderer == without_renderer

    with tempfile.TemporaryDirectory(prefix="volcengine-0.1.24-object-scope-") as tmp:
        dist = Path(tmp) / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True)
        asset = assets / "provider-dialog.js"
        asset.write_text(_dashboard_fixture(), encoding="utf-8")
        index = dist / "index.html"
        index.write_text(
            '<html><script type="module" src="/assets/provider-dialog.js"></script></html>',
            encoding="utf-8",
        )
        selected = _select_compatible_asset(dist)
        assert selected == asset.resolve()
        adapted_index = _adapt_index_file(index, compatible_asset=selected)
        assert adapted_index != index.resolve()
        assert "provider-dialog.js?astrbot_volcengine=" in adapted_index.read_text(encoding="utf-8")
        assert "?astrbot_volcengine=" not in index.read_text(encoding="utf-8")

    print("OBJECT_SCOPED_MODEL_CARD_UI_0_1_24=OK")


if __name__ == "__main__":
    main()
