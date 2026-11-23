"""Dialogue extraction, talk-mode suppression, anti-cliché cues, and TTS sanitation for SandTie."""
from __future__ import annotations

import hashlib
import re

from . import catalogs as _cat
from . import director_cards as _dir

_GLUCK_RX = re.compile(r"\bgluck(?:\s*[,.\-!…]*\s*gluck)*\b", re.I)

_SILENT_RX = re.compile(
    r"\b(?:silent(?:ly)?|in\s+(?:total\s+|complete\s+|utter\s+)?silence|"
    r"(?:no|without|zero)\s+(?:spoken\s+)?(?:dialogue|talking|speech|words|voice(?:\s*lines?)?|vocals?)|"
    r"non[- ]?verbal|mute|speechless|wordless)\b",
    re.I,
)


def sanitize_gluck(q: str) -> str:
    return _GLUCK_RX.sub("Mmmph... hmm!!!", str(q or ""))


def extract_quotes(brief: str) -> list[str]:
    if not brief:
        return []
    out: list[str] = []
    for pat in (r'"([^"\n]{2,220})"', r"“([^”\n]{2,220})”", r"'([^'\n]{3,220})'"):
        for m in re.finditer(pat, brief):
            q = sanitize_gluck(m.group(1).strip())
            if q and q not in out:
                out.append(q)
    return out


def is_silent_request(brief: str, talk_mode: str = "auto", plan: str = "", plan_hint: str = "") -> bool:
    tm = str(talk_mode or "auto").strip().lower()
    if tm == "silent":
        return True
    combined = f"{brief or ''}\n{plan or ''}\n{plan_hint or ''}"
    if _SILENT_RX.search(combined):
        return True
    return False


def should_suppress_dialogue(
    brief: str,
    flavors: dict | None = None,
    plan: str = "",
    quotes: list[str] | None = None,
) -> bool:
    flavors = flavors or {}
    tm = str(flavors.get("talk_mode") or "auto").strip().lower()
    plan_hint = str(flavors.get("plan_hint") or "")
    if is_silent_request(brief, talk_mode=tm, plan=plan, plan_hint=plan_hint):
        return True
    qs = quotes if quotes is not None else extract_quotes(brief)
    if tm == "quotes_only" and not qs:
        return True
    if tm == "auto" and not qs:
        raw_exp = str(flavors.get("explicit") or "").strip()
        eids = [x.lower() for x in _cat.parse_multi_ids(raw_exp)]
        cid = str(flavors.get("camera") or "").strip().lower()
        combined = f"{brief or ''}\n{plan or ''}\n{plan_hint}"
        has_speech_ask = bool(
            re.search(
                r"\b(?:say\w*|speak\w*|talk\w*|whisper\w*|tell\w*|ask\w*|taunt\w*|mock\w*|count\w*|teas\w*|flirt\w*|argu\w*|complain\w*|confess\w*|beg\w*|plead\w*|greet\w*|mutter\w*|murmur\w*|answer\w*|repl\w*|shout\w*|yell\w*|explain\w*|narrat\w*|sing\w*|banter\w*|joi|cei|sph|findom|dialogue|monologue)\b",
                combined,
                re.I,
            )
        )
        if _dir.is_anal(brief, explicit_id=raw_exp, plan=plan, plan_hint=plan_hint) and len(eids) <= 1:
            return True
        if eids and all(eid in _dir.NON_VOCAL_DEFAULT_EXPLICIT_IDS for eid in eids) and not has_speech_ask:
            return True
        if _dir.is_rear_facing(brief, explicit_id=raw_exp, plan=plan, plan_hint=plan_hint, camera_id=cid) and not any(eid in _dir.MIRROR_EXPLICIT_IDS for eid in eids) and not has_speech_ask:
            return True
        if _dir.is_mouth_occupied(brief, explicit_id=raw_exp, plan=plan, plan_hint=plan_hint) and not any(eid in ("rough_deepthroat_mascara", "gloryhole_wall_oral", "bdsm_ballgag_tease") for eid in eids) and not has_speech_ask:
            return True
    return False


_ARC_FALLBACKS = {
    0: [
        "Come closer, right here on the edge.",
        "Keep your eyes right on mine.",
        "Don't hold back, take your time right here.",
        "Right there, stay close while I pull this off.",
        "Wait right there, let me look at you first.",
        "Move in slowly, keep your hands right on my waist.",
        "Stay still for a second while I get comfortable.",
        "Come sit beside me, don't look away yet.",
        "Look up at me while you hold me close.",
        "Lean in a little more, I want you right here.",
    ],
    1: [
        "Mmm, right like that, keep going just like that.",
        "Faster, don't stop now, keep that exact pace.",
        "Ah, right there, stay deep just like that.",
        "Feel how wet and tight this is, keep thrusting.",
        "Yes, right at that angle, keep your grip firm.",
        "Don't slow down yet, keep moving smooth and steady.",
        "Oh, that spot right there, keep pushing deep.",
        "Hold onto my hips and keep that exact rhythm.",
        "Mmm, so warm, stay deep and keep going.",
        "Keep watching my face while you drive deeper.",
    ],
    2: [
        "Yes, right there, keep going until we finish together.",
        "Mmmph, don't pull back now, stay all the way inside.",
        "Right there, so deep, don't stop.",
        "Catch your breath right here, stay pressed tight against me.",
        "Just like that, hold me tight right through the end.",
        "Stay right against me while everything settles.",
        "Mmm, stay close and breathe with me for a moment.",
        "Don't let go yet, stay pressed skin to skin.",
        "Right there, hold steady until my breath slows down.",
        "Stay right here beside me, don't move away yet.",
    ],
}


_SFW_ARC_FALLBACKS = {
    0: [
        "Hold on, did you see that by the window?",
        "Wait a second, let me finish setting this down first.",
        "You made it right on time, come take a look at this.",
        "Look at the street lights coming on outside.",
        "Before we start, tell me what you heard earlier.",
        "Take a seat right across from me for a minute.",
        "Did you bring the folder you mentioned this morning?",
        "Hang on, check the corner table over there first.",
        "You look exhausted, sit down and catch your breath.",
        "Listen closely for a second before anyone walks in.",
    ],
    1: [
        "Keep moving forward, we only get one clean shot at this.",
        "Look closely at what changed since earlier.",
        "Wait, did you hear that right down the hall?",
        "That explains why nobody answered the door before.",
        "Stay sharp, keep your eyes on the far entrance.",
        "I told you we should have checked this room sooner.",
        "Watch how the light catches the edge of the glass.",
        "Keep talking, I want to hear the rest of your plan.",
        "Hold steady right there, let me check the lock.",
        "You were right about that detail from the beginning.",
    ],
    2: [
        "Alright, that settles it. Let's head out.",
        "Good, now we know exactly where things stand.",
        "There it is. Right where we left it.",
        "Okay, we got what we came for, let's go.",
        "That works for me, see you out front in five.",
        "Everything looks clear now, keep pace beside me.",
        "Leave it right there on the counter and let's move.",
        "Finally, that was the piece we were missing.",
        "Perfect, keep that quiet until we reach the car.",
        "Sounds good, lead the way down the stairs.",
    ],
}


_NATIVE_SFW_FALLBACKS = {
    "Japanese": [
        "ちょっと待って、今の見た？",
        "そのまま動かないで、こっちを見て。",
        "ほら、やっと見つかったよ。",
        "静かにして、向こうから足音が聞こえる。",
        "先にこれを確認してから出かけよう。",
        "よし、これで準備は全部整ったね。",
    ],
    "Korean": [
        "잠깐만, 방금 창밖 봤어?",
        "이리 와 봐, 지금부터가 진짜야.",
        "좋아, 이제 다음으로 넘어가자.",
        "조용히 해 봐, 복도 쪽에서 소리 났어.",
        "방금 네가 말한 게 바로 이거였구나.",
        "자, 이제 자리 정리하고 바로 나가자.",
    ],
    "Mandarin": [
        "等一下，你刚才看到窗外了吗？",
        "先别动，仔细看看这里。",
        "好了，现在全都清楚了。",
        "小声点，走廊那边好像有动静。",
        "把桌上的东西拿好，我们马上走。",
        "行，就按刚才说好的办吧。",
    ],
    "Spanish": [
        "Espera un segundo, ¿viste eso por la ventana?",
        "Ven aquí, quédate justo en este lugar.",
        "Perfecto, ahora seguimos adelante juntos.",
        "Escucha bien, alguien acaba de abrir la puerta.",
        "Ten cuidado con el vidrio sobre la mesa.",
        "Listo, ya tenemos todo lo que vinimos a buscar.",
    ],
    "French": [
        "Attends une seconde, tu as vu ça par la fenêtre ?",
        "Viens plus près, regarde bien ce qui change.",
        "Très bien, maintenant on peut y aller.",
        "Écoute un instant, on dirait des pas dehors.",
        "Pose ton manteau ici et assieds-toi vite.",
        "Parfait, on garde ça entre nous pour ce soir.",
    ],
    "Russian": [
        "Подожди секунду, ты видел это у окна?",
        "Подойди ближе и смотри прямо сюда.",
        "Хорошо, теперь всё встало на свои места.",
        "Тише, послушай, там в коридоре кто-то идёт.",
        "Возьми ключи со стола и пойдём быстрее.",
        "Отлично, именно этого нам и не хватало.",
    ],
    "Portuguese": [
        "Espera um segundo, você viu aquilo na janela?",
        "Chega mais perto e olha bem para isso.",
        "Perfeito, agora está tudo no lugar.",
        "Escuta bem, tem alguém subindo a escada agora.",
        "Deixa a bolsa na cadeira e vem ver isto.",
        "Ótimo, já podemos sair antes que escureça.",
    ],
    "Italian": [
        "Aspetta un attimo, hai visto fuori dalla finestra?",
        "Vieni più vicino e guarda qui con calma.",
        "Perfetto, adesso è tutto molto chiaro.",
        "Ascolta bene, si sente qualcuno nel corridoio.",
        "Appoggia pure le chiavi sul tavolo davanti a te.",
        "Benissimo, ora possiamo uscire con calma.",
    ],
}

_NATIVE_NSFW_FALLBACKS = {
    "Japanese": [
        "もっと近くに来て、目をそらさないで。",
        "あっ、そこ、そのまま止めないで動かして。",
        "だめ、奥まで入って、このまま離さないで。",
        "ゆっくり息を整えて、もっと腰を寄せて。",
        "そのままの手つきで、リズムを崩さないで。",
        "いいよ、最後までしっかり抱きしめていて。",
    ],
    "Korean": [
        "더 가까이 와 봐, 내 눈만 바라봐.",
        "아, 거기, 멈추지 말고 계속 움직여 줘.",
        "좋아, 끝까지 들어온 채로 안아 줘.",
        "서두르지 말고, 지금 이 속도 그대로 맞춰 줘.",
        "내 허리를 꽉 잡고 조금만 더 깊게 와 줘.",
        "숨 고르면서 이대로 내 품에 기대 있어.",
    ],
    "Mandarin": [
        "再靠近一点，看着我的眼睛别移开。",
        "嗯，就这样别停，保持这个节奏继续。",
        "好深，就这样紧紧贴在一起别松开。",
        "慢一点，让我先适应你现在的力道。",
        "抓稳我的腰，按刚才那个角度继续。",
        "别急着抽开，就这样抱着我喘口气。",
    ],
    "Spanish": [
        "Acércate más, mírame directo a los ojos.",
        "Así, sigue moviéndote despacio sin parar.",
        "Quédate bien adentro, pegado contra mí.",
        "Sujétame fuerte de la cintura y no pierdas el ritmo.",
        "Un poco más lento, quédate justo en ese punto.",
        "Respira conmigo así, pegado piel con piel.",
    ],
    "French": [
        "Approche-toi encore, garde les yeux sur moi.",
        "Oui, comme ça, continue exactement ce rythme.",
        "Reste tout au fond, serré contre moi.",
        "Serre mes hanches un peu plus fort maintenant.",
        "Ne change rien, garde exactement cette cadence.",
        "Reste contre ma peau le temps de reprendre souffle.",
    ],
    "Russian": [
        "Подойди ближе и смотри прямо мне в глаза.",
        "Вот так, не останавливайся, двигайся глубже.",
        "Останься внутри до самого конца, прижмись ко мне.",
        "Держи меня крепче за талию и не сбивай ритм.",
        "Чуть медленнее, вот так прямо в точку.",
        "Не отпускай меня ещё минуту, дыши рядом.",
    ],
    "Portuguese": [
        "Chega mais perto, olha direto nos meus olhos.",
        "Isso, continua nesse ritmo sem parar agora.",
        "Fica bem fundo assim, colado em mim.",
        "Segura firme na minha cintura e mantém essa cadência.",
        "Devagar desse jeito, não muda o ângulo agora.",
        "Fica aqui bem junto enquanto a respiração acalma.",
    ],
    "Italian": [
        "Avvicinati ancora, tienimi gli occhi addosso.",
        "Sì, proprio così, continua con questo ritmo.",
        "Resta tutto dentro, stretto contro di me.",
        "Stringimi forte sui fianchi e non perdere il passo.",
        "Più piano così, resta esattamente su quel punto.",
        "Resta stretto contro di me finché non riprendi fiato.",
    ],
}

_NATIVE_LANG_SCRIPT_RX = {
    "Japanese": re.compile(r"[\u3040-\u30ff]"),
    "Korean": re.compile(r"[\uac00-\ud7af]"),
    "Mandarin": re.compile(r"[\u4e00-\u9fff]"),
    "Chinese": re.compile(r"[\u4e00-\u9fff]"),
    "Russian": re.compile(r"[\u0400-\u04ff]"),
    "Spanish": re.compile(r"[áéíóúüñ¿¡]|\b(?:qué|como|cómo|más|aquí|ahora|esto|está|estás|contigo|conmigo|quiero|ven|mira|todo|bien|así|sin|para)\b", re.I),
    "French": re.compile(r"[àâçéèêëîïôûùüÿœ]|\b(?:je|tu|nous|vous|avec|sans|comme|encore|viens|ici|plus|près|oui|bien|tout|c'est|maintenant|regarde)\b", re.I),
    "Portuguese": re.compile(r"[ãõáéíóúâêôç]|\b(?:você|aqui|agora|mais|perto|vem|olha|comigo|assim|tudo|meu|minha|isso|sem|para)\b", re.I),
    "Italian": re.compile(r"[àèéìíîòóùú]|\b(?:ciao|vieni|qui|guarda|ancora|questo|questa|adesso|sempre|così|tutto|mio|mia|con|senza)\b", re.I),
}


def detect_target_language(brief: str = "", acc_opt: dict | None = None) -> str:
    """Resolve the requested spoken language (e.g. 'Japanese', 'Korean', 'English')."""
    if acc_opt:
        lang = str(acc_opt.get("lang") or "").strip()
        if lang and lang.lower() != "english":
            return lang
        acc_id = str(acc_opt.get("id") or "").lower()
        if acc_id == "japanese_native_anime":
            return "Japanese"
        if acc_id == "korean_native_seoul":
            return "Korean"
        if acc_id == "mandarin_native_beijing":
            return "Mandarin"
    b = str(brief or "")
    if b:
        for pat, name in (
            (r"\b(?:in\s+japanese|speaks?\s+japanese|japanese\s+(?:dialogue|voice|lines?|speech))\b|[\u3040-\u30ff]", "Japanese"),
            (r"\b(?:in\s+korean|speaks?\s+korean|korean\s+(?:dialogue|voice|lines?|speech))\b|[\uac00-\ud7af]", "Korean"),
            (r"\b(?:in\s+(?:mandarin|chinese)|speaks?\s+(?:mandarin|chinese)|(?:mandarin|chinese)\s+(?:dialogue|voice|lines?|speech))\b", "Mandarin"),
            (r"\b(?:in\s+spanish|speaks?\s+spanish|spanish\s+(?:dialogue|voice|lines?|speech))\b", "Spanish"),
            (r"\b(?:in\s+french|speaks?\s+french|french\s+(?:dialogue|voice|lines?|speech))\b", "French"),
            (r"\b(?:in\s+russian|speaks?\s+russian|russian\s+(?:dialogue|voice|lines?|speech))\b|[\u0400-\u04ff]", "Russian"),
            (r"\b(?:in\s+portuguese|speaks?\s+portuguese|portuguese\s+(?:dialogue|voice|lines?|speech))\b", "Portuguese"),
            (r"\b(?:in\s+italian|speaks?\s+italian|italian\s+(?:dialogue|voice|lines?|speech))\b", "Italian"),
        ):
            if re.search(pat, b, re.I):
                return name
    return "English"


def language_script_missing(text: str, target_lang: str) -> bool:
    """Return True if <d>...</d> lines (or lyrics) lack native script for `target_lang`."""
    lang = str(target_lang or "").strip()
    if not lang or lang.lower() in ("auto", "english"):
        return False
    rx = _NATIVE_LANG_SCRIPT_RX.get(lang)
    if rx is None:
        return False
    d_matches = re.findall(r"<d>(.*?)</d>", str(text or ""), flags=re.S | re.I)
    if not d_matches:
        return False
    # Strip delivery tag [Japanese, ...] before checking spoken content
    spoken = " ".join(re.sub(r"^\s*\[[^\]]*\]\s*", "", d) for d in d_matches).strip()
    if not spoken:
        return False
    return not bool(rx.search(spoken))


def native_sample_for(target_lang: str) -> str:
    pool = _NATIVE_SFW_FALLBACKS.get(target_lang)
    return pool[0] if pool else ""


def pick_beat_dialogue_cues(
    *,
    brief: str = "",
    talk_opt: dict | None = None,
    acc_opt: dict | None = None,
    playbook_entries: list[dict] | None = None,
    n_beats: int = 3,
    is_sexual_scene: bool = False,
) -> list[str]:
    """Deterministic, varied Beat 1/2/3 dialogue suggestions so no stale template line ever repeats."""
    target_lang = detect_target_language(brief, acc_opt)
    seed_src = f"{brief}|{(talk_opt or {}).get('id', '')}|{(acc_opt or {}).get('id', '')}|{'/'.join(p.get('title','') for p in (playbook_entries or []))}"
    h_idx = int(hashlib.sha1(seed_src.encode("utf-8", "ignore")).hexdigest()[:8], 16)

    small_words: list[str] = []
    if talk_opt and talk_opt.get("small"):
        small_words = [x.strip() for x in str(talk_opt["small"]).split(",") if x.strip()]
    pb_phrases: list[str] = []
    for pb in playbook_entries or []:
        for p in pb.get("phrases") or []:
            if str(p or "").strip():
                pb_phrases.append(str(p).strip())

    out: list[str] = []
    used: set[str] = set()

    def _pick_unique(pool_list: list[str], step: int) -> str:
        n_p = len(pool_list)
        for off in range(n_p):
            cand = pool_list[(h_idx + step + off) % n_p]
            if cand not in used:
                used.add(cand)
                return cand
        return pool_list[(h_idx + step) % n_p]

    for b in range(max(1, n_beats)):
        arc_b = 0 if b == 0 else (2 if b == n_beats - 1 else 1)
        if target_lang != "English":
            native_pool = (_NATIVE_NSFW_FALLBACKS if is_sexual_scene else _NATIVE_SFW_FALLBACKS).get(target_lang)
            if native_pool:
                out.append(_pick_unique(native_pool, b))
                continue
        if b < len(pb_phrases):
            used.add(pb_phrases[b])
            out.append(pb_phrases[b])
        elif is_sexual_scene:
            pool = _ARC_FALLBACKS[arc_b]
            line = _pick_unique(pool, b * 3)
            if small_words and b == 0:
                tok = small_words[h_idx % len(small_words)]
                if len(tok) <= 32 and tok.lower() not in line.lower():
                    line = f"{tok.rstrip('.!~')}, {line[0].lower() + line[1:]}"
            out.append(line)
        else:
            pool = _SFW_ARC_FALLBACKS[arc_b]
            out.append(_pick_unique(pool, b * 3))
    return out
