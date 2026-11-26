"""H3 Chain Preview -- the chain's progress panel, as its own node.

Split off `HandTieClips` deliberately. That node already carries a 21-widget shot
editor and a reference rail; folding a large media panel onto it as well makes
an unreadable node, and the panel wants to be somewhere else in the graph
anyway -- on the IMAGE wire, right before CreateVideo, where the thing being
previewed actually flows.

It is a passthrough: images and audio go straight out again, unchanged, so
dropping it into an existing chain costs nothing and removing it changes no
pixels. What it adds is a place for the live `h3_refchain_preview` events to
land, and an end-of-run report of the two numbers the chain never surfaced --
which pin mechanism each hop actually used, and how far the audio has drifted
from the video.
"""
from __future__ import annotations
from comfy_api.latest import io

try:
    from server import PromptServer
except Exception:  # noqa: BLE001 -- headless / API-only runs have no server
    PromptServer = None

TAG = "HTCChainPreview"
FPS = 24


def _send(payload):
    if PromptServer is None:
        return
    try:
        PromptServer.instance.send_sync(
            "h3_chain_preview", payload, PromptServer.instance.client_id)
    except Exception as e:  # noqa: BLE001
        print(f"[{TAG}] preview send skipped: {e!r}", flush=True)


class _HTCChainPreviewImpl:
    """Pass images and audio through, and report the join.

    Wire between HandTieClips and CreateVideo.
    """


    def run(self, images, audio=None, info="", unique_id=None):
        frames = int(images.shape[0]) if images is not None else 0
        video_s = frames / float(FPS)
        # A dry run compiles prompts and hands back ONE placeholder frame at the
        # resolution the plan resolved to. Reporting A/V drift from that is
        # reporting a number about nothing: the run printed "1f / 0.04s video,
        # 0.02s audio, drift -18 ms", which reads exactly like a measurement of
        # a real chain and describes a frame that was never rendered.
        #
        # `info` is how it is known, rather than a frame count: the chain writes
        # its DRY RUN banner as the first line, so this is what actually
        # happened rather than a guess from the shape of the tensor.
        dry = str(info or "").lstrip().startswith("DRY RUN")
        payload = {
            "node_id": unique_id,
            "frames": frames,
            "video_s": round(video_s, 3),
            "width": int(images.shape[2]) if frames else 0,
            "height": int(images.shape[1]) if frames else 0,
            "dry_run": dry,
        }

        if dry:
            print(f"[{TAG}] dry run: prompts compiled, nothing rendered -- "
                  f"no drift to measure. The placeholder is "
                  f"{payload['width']}x{payload['height']}, the size the plan "
                  f"resolved to.", flush=True)
        elif isinstance(audio, dict) and audio.get("waveform") is not None:
            wav = audio["waveform"]
            sr = int(audio.get("sample_rate") or 0)
            if sr:
                audio_s = float(wav.shape[-1]) / float(sr)
                drift_ms = (audio_s - video_s) * 1000.0
                payload["audio_s"] = round(audio_s, 3)
                payload["sample_rate"] = sr
                payload["drift_ms"] = round(drift_ms, 1)
                # Worth a console line too: it is cumulative across a chain and
                # nothing else in the pack reports it.
                print(f"[{TAG}] {frames}f / {video_s:.2f}s video, "
                      f"{audio_s:.2f}s audio, drift {drift_ms:+.0f} ms", flush=True)
        if info:
            info_s = str(info)
            payload["info"] = info_s
            for ln in info_s.splitlines():
                low = ln.strip().lower()
                if low.startswith("seam health:"):
                    payload["seam_health"] = ln.split(":", 1)[1].strip()
                elif low.startswith("motion overload:"):
                    payload["motion_overload"] = ln.split(":", 1)[1].strip()

        _send(payload)
        return (images, audio)


class HTCChainPreview(io.ComfyNode, _HTCChainPreviewImpl):
    """V3 schema for HTCChainPreview; the implementation lives in _HTCChainPreviewImpl.

    Also inherits _HTCChainPreviewImpl so existing callers of the V1 API (HTCChainPreview().run(...),
    HTCChainPreview.<helper>) keep working; core sees only the V3 hooks below."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='HTCChainPreview',
            display_name='H3 Chain Preview',
            category="Hand Tie Clips",
            description="Preview panel for an H3 Ref2VA chain. Sits on the IMAGE wire before "
                "CreateVideo and passes images and audio through untouched. Shows the "
                "live sample, per-hop progress, which pin mechanism each hop used "
                "(Motion-Context vs the AddGuide fallback), and end-of-run A/V drift.",
            inputs=[
                io.Image.Input(
                    'images',
                    tooltip="Generated video frames from HandTieClips. Passed through untouched for live preview and end-of-run diagnostics.",
                ),
                io.Audio.Input(
                    'audio',
                    optional=True,
                    tooltip="Generated soundtrack from HandTieClips. Wire it to measure A/V sync drift against the video frames.",
                ),
                io.String.Input(
                    'info',
                    optional=True,
                    force_input=True,
                    tooltip="The info string from HandTieClips. Feeds seam health, motion overload, and hop diagnostics into the preview card.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name='images'),
                io.Audio.Output(display_name='audio'),
            ],
            hidden=[io.Hidden.unique_id],
        )

    @classmethod
    def execute(cls, **kwargs):
        kwargs['unique_id'] = cls.hidden.unique_id
        result = _HTCChainPreviewImpl().run(**kwargs)
        if isinstance(result, dict):
            return io.NodeOutput.from_dict(result)
        return io.NodeOutput(*result) if result is not None else io.NodeOutput()


# -- pre-rename ids ----------------------------------------------------------
# A plain alias in NODE_CLASS_MAPPINGS keeps old workflows loading, but it also
# lists the node a second time in search: ComfyUI falls back to the mapping key
# when NODE_DISPLAY_NAME_MAPPINGS has no entry. Subclassing and setting
# DEPRECATED gets both -- server.py publishes `deprecated: True`, and the
# frontend's `Comfy.Node.ShowDeprecated` (off by default) hides it from search
# while leaving it fully functional in workflows that name it.


class _LegacyH3ChainPreview(HTCChainPreview):
    """Old node id 'H3ChainPreview': same node as HTCChainPreview, kept so old workflows load."""

    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        schema.node_id = 'H3ChainPreview'
        schema.display_name = 'H3ChainPreview'
        schema.is_deprecated = True
        return schema


NODE_CLASS_MAPPINGS = {
    "HTCChainPreview": HTCChainPreview,
    "H3ChainPreview": _LegacyH3ChainPreview,
}
NODE_DISPLAY_NAME_MAPPINGS = {"HTCChainPreview": "H3 Chain Preview"}
