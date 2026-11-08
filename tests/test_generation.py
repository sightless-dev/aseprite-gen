import json
from pathlib import Path
import pytest
from PIL import Image
from aseprite_gen.aseprite import validate_scene
from aseprite_gen.generation import plan, parse_prompt, load_profile
from aseprite_gen.validation import review_png, preview


@pytest.mark.parametrize("kind,size",[("bush",(48,48)),("tree",(64,96)),("barrel",(32,32))])
def test_native_plans_are_repeatable_and_valid(kind,size):
    first,metadata=plan(kind,seed=7)
    assert first==plan(kind,seed=7)[0]
    valid=validate_scene(first)
    assert (valid["width"],valid["height"])==size
    assert len(valid["palette"])<=24
    assert len({layer["name"] for layer in valid["layers"]})==len(valid["layers"])
    assert metadata["visual_review"]=="pending"
    assert first != plan(kind,seed=8)[0]


@pytest.mark.parametrize("kind",["bush","tree","barrel"])
def test_requested_canvas_and_autumn_remain_pixel_bounded(kind):
    scene,metadata=plan("autumn "+kind,width=29,height=37)
    validate_scene(scene)
    assert (scene["width"],scene["height"])==(29,37)
    assert metadata["spec"]["autumn"]


def test_semantics_are_bounded_and_russian_wood_does_not_select_tree():
    assert parse_prompt("старая деревянная бочка")["kind"]=="barrel"
    assert parse_prompt("осенний куст с ягодами")["berries"]
    with pytest.raises(ValueError):plan("spaceship")
    with pytest.raises(ValueError):plan("tree",width=0,height=10)


def test_persistent_profile_controls_geometry_not_only_metadata(tmp_path):
    original=load_profile()
    profile=tmp_path/"style.json"
    profile.write_text(json.dumps(original))
    first=plan("bush",seed=7,profile=profile)[0]
    original["geometry"]["bush"]["crown"][2]=14
    original["leaf_clusters"]["spacing"]=4.8
    profile.write_text(json.dumps(original))
    changed=plan("bush",seed=7,profile=profile)[0]
    validate_scene(changed)
    assert first["layers"]!=changed["layers"]
    assert len(first["layers"][1]["operations"])!=0


def test_unsupported_profile_schema_fails_before_rendering(tmp_path):
    profile=tmp_path/"old.json"
    profile.write_text(json.dumps({"schema_version":1}))
    with pytest.raises(ValueError,match="schema 2"):
        plan("bush",profile=profile)


def test_metrics_detect_alpha_palette_and_dimensions_without_art_verdict(tmp_path):
    image=Image.new("RGBA",(4,4));image.putpixel((1,1),(200,30,50,128))
    path=tmp_path/"bad.png";image.save(path)
    report=review_png(path,expected_size=(8,8),palette=["#ffffff"])
    assert not report["technical_pass"]
    assert len(report["errors"])==3
    assert "unreviewed" in report["artistic_verdict"]
    large=tmp_path/"preview.png";preview(path,large,3)
    with Image.open(large) as read:
        assert read.size==(12,12)
        assert read.getpixel((3,3))==(200,30,50,128)


@pytest.mark.integration
def test_generate_review_commands_reopen_actual_source(tmp_path,capfd):
    from aseprite_gen.cli import main
    from aseprite_gen.aseprite import find_aseprite
    try:find_aseprite()
    except FileNotFoundError:pytest.skip("Aseprite is required")
    assert main(["generate","berry bush","--name","sample","--output",str(tmp_path)])==0
    capfd.readouterr()
    # Review must render the source, independent of a stale adjacent PNG.
    (tmp_path/"sample.png").write_bytes(b"not a png")
    assert main(["review",str(tmp_path/"sample.aseprite"),"--output",str(tmp_path)])==0
    result=json.loads(capfd.readouterr().out)
    assert result["technical_review"]["technical_pass"]
    with Image.open(tmp_path/"sample.review-native.png") as image:
        assert image.size==(48,48)
    meta=json.loads((tmp_path/"sample.generation.json").read_text())
    assert meta["render"]["aseprite_path"]=="sample.aseprite"
