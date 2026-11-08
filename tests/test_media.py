from __future__ import annotations

import os

import pytest

from hermes_fal_video.media import MediaError, prepare

MB = 1024 * 1024


def test_https_urls_pass_through_without_upload(fake_client) -> None:
    assert prepare(" https://cdn.example/clip.mp4 ", "video", fake_client, MB) == \
        "https://cdn.example/clip.mp4"
    assert fake_client.uploads == []


def test_local_and_file_url_media_is_uploaded(fake_client, tmp_path) -> None:
    clip = tmp_path / "clip.MP4"
    clip.write_bytes(b"\0" * 10)
    assert prepare(str(clip), "video", fake_client, MB).endswith("/clip.MP4")
    assert prepare(clip.as_uri(), "video", fake_client, MB).endswith("/clip.MP4")
    assert fake_client.uploads == [clip.resolve(), clip.resolve()]


@pytest.mark.parametrize("name", [".env", "id_rsa", "notes.txt", "clip.mp4.sh"])
def test_non_media_files_are_never_uploaded(fake_client, tmp_path, name) -> None:
    target = tmp_path / name
    target.write_text("secret")
    with pytest.raises(MediaError, match="must end in"):
        prepare(str(target), "video", fake_client, MB)
    assert fake_client.uploads == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks")
def test_media_named_symlink_to_a_secret_is_refused(fake_client, tmp_path) -> None:
    secret = tmp_path / "credentials"
    secret.write_text("token")
    link = tmp_path / "innocent.png"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("symlinks not permitted")
    with pytest.raises(MediaError, match="must end in"):
        prepare(str(link), "image", fake_client, MB)
    assert fake_client.uploads == []


def test_image_suffixes_do_not_cover_video(fake_client, tmp_path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\0")
    with pytest.raises(MediaError):
        prepare(str(clip), "image", fake_client, MB)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("ftp://host/clip.mp4", "Unsupported media source scheme"),
        ("data:video/mp4;base64,AAAA", "Unsupported media source scheme"),
        ("https://", "Not a valid URL"),
        ("/does/not/exist.mp4", "not found"),
        ("", "Expected a video"),
    ],
)
def test_bad_sources(fake_client, source, message) -> None:
    with pytest.raises(MediaError, match=message):
        prepare(source, "video", fake_client, MB)


def test_size_limits(fake_client, tmp_path) -> None:
    empty = tmp_path / "empty.webm"
    empty.write_bytes(b"")
    big = tmp_path / "big.webm"
    big.write_bytes(b"\0" * (MB + 1))
    with pytest.raises(MediaError, match="empty"):
        prepare(str(empty), "video", fake_client, MB)
    with pytest.raises(MediaError, match="over 1 MB"):
        prepare(str(big), "video", fake_client, MB)
    assert fake_client.uploads == []


def test_file_url_with_escaped_characters(fake_client, tmp_path) -> None:
    clip = tmp_path / "my clip.mov"
    clip.write_bytes(b"\0")
    assert "%20" in clip.as_uri()
    assert prepare(clip.as_uri(), "video", fake_client, MB).endswith("/my clip.mov")
    assert fake_client.uploads == [clip.resolve()]
