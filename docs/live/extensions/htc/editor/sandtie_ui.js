/* SANDTIE UI (js/editor/sandtie_ui.js)
 *
 * Unified clean-room R2-styled SandTie Scribe / PromptRig interface powering:
 *   1. HandTieClips' reworked `Standard` tab (`mountSandTieInStandard`)
 *   2. Standalone `SandTiePromptRig` node pop-out (`mountSandTieStandalone`)
 *   3. SWAP's optional Speech/Accent/Style extras (`mountSwapExtras`)
 */
import { el, button, widgetByName } from "./widget_utils.js";

const LLM_URL = "/h3_ref_chain/llm";
const SANDTIE_OPTIONS_URL = "/h3_ref_chain/sandtie/options";
const SANDTIE_WRITE_URL = "/h3_ref_chain/sandtie/write";
const SANDTIE_EXTRACT_URL = "/h3_ref_chain/sandtie/extract_video";
const SANDTIE_PRESET_URL = "/h3_ref_chain/sandtie/preset";
const SANDTIE_REFBANK_URL = "/h3_ref_chain/sandtie/ref_bank";
const SANDTIE_THUMB_URL = "/h3_ref_chain/sandtie/thumb";
const UPLOAD_URL = "/h3_ref_chain/upload";
const FLAVOR_PROP = "h3_standard_flavors";

const MSEL_STYLE_ID = "h3e-sandtie-msel-style";
const MSEL_CSS = `
/* -- SandTie PromptRig: multi-select popovers & R2 cards ---------------- */
.h3st-shell { display: flex; flex-direction: column; gap: 8px; }
.h3st-head { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: space-between; }
.h3st-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.h3st-sw-bar {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 5px 8px; background: var(--h3-sunken);
    border: 1px solid var(--h3-border-soft); border-radius: var(--h3-radius-sm);
}
.h3st-sw {
    display: inline-flex; align-items: center; gap: 4px; cursor: pointer; user-select: none;
    font-size: var(--h3-fs-sm); color: var(--h3-text); padding: 2px 5px; border-radius: 3px;
}
.h3st-sw:hover { background: rgba(255,255,255,0.04); }
.h3st-sw input { width: auto; margin: 0; accent-color: var(--h3-accent); cursor: pointer; }
.h3st-grid-primary {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(185px, 1fr)); gap: 5px;
}
.h3st-drawer {
    padding: 8px; background: var(--h3-sunken);
    border: 1px solid var(--h3-border-soft); border-radius: var(--h3-radius);
    display: flex; flex-direction: column; gap: 6px;
}
.h3st-drawer[hidden] { display: none !important; }
.h3st-bible {
    padding: 8px; background: var(--h3-sunken);
    border: 1px solid var(--h3-border); border-radius: var(--h3-radius);
    display: flex; flex-direction: column; gap: 6px;
}
.h3st-bible-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(235px, 1fr));
    gap: 6px; max-height: 250px; overflow-y: auto; scrollbar-width: thin;
}
.h3st-bcard {
    background: var(--h3-panel); border: 1px solid var(--h3-border);
    border-radius: var(--h3-radius-sm); padding: 6px; display: flex; flex-direction: column; gap: 4px;
}
.h3st-bcard.h3st-bwired {
    border-color: color-mix(in srgb, var(--h3-accent) 75%, var(--h3-border));
    background: color-mix(in srgb, var(--h3-accent) 6%, var(--h3-panel));
}
.h3st-btop { display: flex; gap: 7px; align-items: center; }
.h3st-bthumb {
    width: 40px; height: 40px; flex: 0 0 40px; border-radius: 3px;
    object-fit: cover; background: #181a20; border: 1px solid var(--h3-border);
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 700; color: var(--h3-accent);
}
.h3st-bdesc {
    font-size: 10.5px; color: var(--h3-muted);
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.h3st-pill {
    display: inline-flex; align-items: center; gap: 4px; padding: 2px 6px;
    border-radius: 3px; font-size: 10.5px; font-weight: 600;
    border: 1px solid var(--h3-border); background: var(--h3-sunken); color: var(--h3-muted);
}
.h3st-pill-accent { border-color: rgba(232,255,71,0.55); background: rgba(232,255,71,0.12); color: var(--h3-accent); }
.h3st-pill-ok { border-color: rgba(95,191,122,0.5); background: rgba(95,191,122,0.13); color: #8ee5a8; }
.h3st-pill-warn { border-color: rgba(255,176,32,0.65); background: rgba(255,176,32,0.16); color: #ffd176; cursor: pointer; }
.h3st-chips { display: inline-flex; align-items: center; gap: 3px; background: var(--h3-sunken); border: 1px solid var(--h3-border-soft); border-radius: 3px; padding: 2px 4px; }
.h3st-chips-lbl { font-size: 10px; font-weight: 700; letter-spacing: 0.05em; color: var(--h3-muted); padding: 0 3px; }
.h3st-chip-on { border-color: var(--h3-accent) !important; color: var(--h3-accent) !important; background: rgba(232,255,71,0.12) !important; }
.h3st-perf-box {
    padding: 7px 8px; background: var(--h3-sunken);
    border: 1px solid var(--h3-border-soft); border-radius: var(--h3-radius);
    display: flex; flex-direction: column; gap: 6px;
}
.h3st-perf-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 6px;
}
.h3st-pcard {
    background: var(--h3-panel); border: 1px solid var(--h3-border-soft);
    border-radius: var(--h3-radius-sm); padding: 6px 7px; display: flex; flex-direction: column; gap: 4px;
}
.h3st-pcard.is-non-zero { border-color: rgba(232,255,71,0.42); }
.h3st-pcard-top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.h3st-ptit { font-size: 10px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--h3-muted); }
.h3st-pval { font-size: 10px; font-weight: 700; font-family: ui-monospace, Consolas, monospace; color: var(--h3-accent); }
.h3st-psteps { display: flex; gap: 2px; flex-wrap: nowrap; }
.h3e-root .h3st-pbtn {
    flex: 1 1 0; min-width: 0; padding: 3px 2px; font-size: 10px; font-weight: 600;
    background: var(--h3-sunken); color: var(--h3-muted); border: 1px solid var(--h3-border); border-radius: 2px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.h3e-root .h3st-pbtn:hover { color: var(--h3-text); border-color: rgba(232,255,71,0.5); }
.h3e-root .h3st-pbtn.h3st-chip-on { border-color: var(--h3-accent); background: rgba(232,255,71,0.16); color: var(--h3-accent); }
.h3st-pdesc { font-size: 10px; color: var(--h3-faint); line-height: 1.25; }
.h3st-aux-row {
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    padding-top: 4px; border-top: 1px solid var(--h3-border-soft);
}

.h3e-msel { position: relative; flex: 1 1 170px; min-width: 140px; display: inline-flex; }
.h3e-root .h3e-msel-btn {
    width: 100%; display: flex; align-items: center; justify-content: space-between;
    gap: 5px; padding: 5px 7px; background: var(--h3-sunken);
    border: 1px solid var(--h3-border); border-radius: var(--h3-radius-sm);
    color: var(--h3-text); font-size: var(--h3-fs-sm); text-align: left; overflow: hidden;
}
.h3e-root .h3e-msel-btn:hover,
.h3e-msel.h3e-msel-open > .h3e-msel-btn { border-color: color-mix(in srgb, var(--h3-accent) 65%, var(--h3-border)); }
.h3e-msel.h3e-msel-active > .h3e-msel-btn {
    border-color: color-mix(in srgb, var(--h3-accent) 85%, var(--h3-border));
    background: color-mix(in srgb, var(--h3-accent) 9%, var(--h3-sunken));
}
.h3e-msel-txt { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.h3e-msel-badge {
    flex: 0 0 auto; background: var(--h3-accent); color: var(--h3-on-accent);
    font-size: var(--h3-fs-xs); font-weight: 700; padding: 0 5px; border-radius: 2px; line-height: 1.4;
}
.h3e-msel-caret { flex: 0 0 auto; color: var(--h3-faint); font-size: var(--h3-fs-xs); line-height: 1; }
.h3e-msel-pop {
    position: absolute; top: calc(100% + 3px); left: 0; z-index: 60;
    min-width: min(310px, 85vw); max-width: min(460px, 92vw); width: max-content;
    background: var(--h3-panel);
    border: 1px solid color-mix(in srgb, var(--h3-accent) 55%, var(--h3-border));
    border-radius: var(--h3-radius); box-shadow: 0 10px 28px rgba(0,0,0,0.72);
    display: flex; flex-direction: column; overflow: hidden;
}
.h3e-msel [hidden],
.h3e-msel-pop[hidden],
.h3e-msel-item[hidden],
.h3e-msel-grp[hidden] { display: none !important; }
.h3e-msel-pop.h3e-msel-right { left: auto; right: 0; }
.h3e-msel-pop.h3e-msel-up { top: auto; bottom: calc(100% + 3px); }
.h3e-msel-head {
    display: flex; align-items: center; gap: 4px; padding: 5px 6px;
    background: var(--h3-bg); border-bottom: 1px solid var(--h3-border-soft);
}
.h3e-root .h3e-msel-search { flex: 1 1 auto; min-width: 90px; font-size: var(--h3-fs-sm); padding: 3px 6px; }
.h3e-root .h3e-msel-mode,
.h3e-root .h3e-msel-clear {
    flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
    line-height: 1.1; font-size: var(--h3-fs-xs); padding: 3px 6px;
}
.h3e-root .h3e-msel-mode.h3e-on {
    border-color: var(--h3-accent); color: var(--h3-accent);
    background: color-mix(in srgb, var(--h3-accent) 14%, var(--h3-panel));
}
.h3e-msel-sub {
    padding: 3px 8px; font-size: var(--h3-fs-xs); color: var(--h3-muted);
    background: var(--h3-sunken); border-bottom: 1px solid var(--h3-border-soft);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.h3e-msel-list { max-height: 290px; overflow-y: auto; overflow-x: hidden; scrollbar-width: thin; padding: 3px 0; }
.h3e-msel-grp {
    padding: 5px 8px 2px; font-size: var(--h3-fs-xs); font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase; color: var(--h3-accent);
    background: color-mix(in srgb, var(--h3-bg) 60%, transparent);
    border-top: 1px solid var(--h3-border-soft);
}
.h3e-msel-grp:first-child { border-top: 0; }
.h3e-msel-item {
    display: flex; align-items: center; gap: 6px; padding: 4px 8px;
    font-size: var(--h3-fs-sm); color: var(--h3-text); cursor: pointer; user-select: none;
    content-visibility: auto; contain-intrinsic-size: auto 26px;
}
.h3e-msel-item:hover { background: color-mix(in srgb, var(--h3-accent) 12%, var(--h3-panel)); }
.h3e-msel-item.h3e-msel-checked { background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-panel)); }
.h3e-root .h3e-msel-item input[type="checkbox"] { width: auto; margin: 0; flex: 0 0 auto; accent-color: var(--h3-accent); cursor: pointer; }
.h3e-msel-ord {
    flex: 0 0 auto; min-width: 18px; height: 16px; padding: 0 4px; border-radius: 2px;
    background: var(--h3-accent); color: var(--h3-on-accent); font-size: var(--h3-fs-xs); font-weight: 700;
    display: inline-flex; align-items: center; justify-content: center; line-height: 1;
}
.h3e-msel-ord:empty { display: none; }
.h3e-msel-lbl { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.h3e-msel-tag {
    flex: 0 0 auto; font-size: 9.5px; font-weight: 700; padding: 1px 4px; border-radius: 2px;
    border: 1px solid var(--h3-border); color: var(--h3-muted); background: var(--h3-bg);
}
.h3e-msel-tag.asp-916 { color: #7dd3fc; border-color: rgba(125,211,252,0.45); background: rgba(14,116,144,0.22); }
.h3e-msel-tag.asp-169 { color: #fcd34d; border-color: rgba(252,211,77,0.45); background: rgba(180,83,9,0.22); }
.h3e-msel-tag.dur-tag { color: #a7f3d0; border-color: rgba(95,191,122,0.4); background: rgba(16,85,55,0.22); }
.h3st-vdrop {
    position: relative; width: 72px; height: 42px; flex: 0 0 72px;
    border: 1px dashed var(--h3-border); border-radius: var(--h3-radius-sm);
    background: var(--h3-panel); color: var(--h3-muted);
    display: flex; align-items: center; justify-content: center;
    text-align: center; cursor: pointer; overflow: hidden; user-select: none;
    transition: border-color 0.15s ease, background 0.15s ease;
}
.h3st-vdrop:hover,
.h3st-drawer.is-dragover .h3st-vdrop,
.h3st-vdrop.is-dragover {
    border-color: var(--h3-accent);
    background: color-mix(in srgb, var(--h3-accent) 12%, var(--h3-panel));
    color: var(--h3-text);
}
.h3st-drawer.is-dragover {
    border-color: var(--h3-accent);
    background: color-mix(in srgb, var(--h3-accent) 6%, var(--h3-sunken));
}
.h3st-vdrop video { width: 100%; height: 100%; object-fit: cover; display: block; }
.h3st-vdrop-hint { font-size: 9.5px; line-height: 1.15; padding: 2px 4px; white-space: pre-line; }
`;

function ensureMselStyle() {
    let st = document.getElementById(MSEL_STYLE_ID);
    if (!st) {
        st = document.createElement("style");
        st.id = MSEL_STYLE_ID;
        document.head.appendChild(st);
    }
    if (st.textContent !== MSEL_CSS) st.textContent = MSEL_CSS;
}

export const BUILTIN_DIAL_COMBOS = [
    { id: "__builtin_noir_rainy_cafe_confession", label: "SFW Noir Drama: Rainy Corner Café Quiet Confession", values: { style: "h3_astro_cinema", camera: "table_two_shot_profile_to_single", place: "cafe_rain_window", light: "soft_natural_window", wardrobe: "tailored_black_blazer_trousers", talkstyle: "earnest_dramatic_confession", ambience: "cafe", music: "piano_cello_65", colour: "kodak_vision3_500t", motion: "slow", energy: "calm", expression: "subtle", expr_read: "tense", life: "natural" } },
    { id: "__builtin_ultrareal_daylight_matte_169", label: "🎞️ Ultra-Realism Rig: Raw Matte Skin, North Window & 35mm Grain (16:9)", values: { style: "style_ultrareal_matte_35mm", camera: "push_in", place: "plate_real_lived_in_living_room_sofa", light: "light_ultrareal_north_window_matte", lens: "cam_cooke_anamm_raw_50mm", colour: "colour_ultrareal_kodak_250d_grain", fx: "fx_ultrareal_35mm_celluloid_grain", fx_timing: "from_start", ambience: "room_tone", motion: "natural", energy: "calm", expression: "subtle", expr_read: "warm", life: "natural" } },
    { id: "__builtin_ultrareal_night_practical_916", label: "📷 Ultra-Realism Rig: Raw Sensor Portrait, Single Lamp & Grain (9:16)", values: { style: "style_ultrareal_raw_sensor_doc", camera: "handheld", place: "plate_real_night_bedside_lamp_bedroom", light: "light_ultrareal_single_practical_raw", lens: "cam_cooke_anamm_raw_50mm", colour: "colour_ultrareal_neutral_rec709", fx: "fx_ultrareal_35mm_celluloid_grain", fx_timing: "from_start", ambience: "room_tone", motion: "natural", energy: "calm", expression: "subtle", expr_read: "warm", life: "natural" } },
    { id: "__builtin_rooftop_skyline_banter", label: "SFW Cinema: Golden-Hour Rooftop Skyline Talk", values: { style: "h3_astro_cinema", camera: "arc_right", place: "plate_luxury_rooftop_infinity_pool", light: "sunset_silhouette_halo_rim", wardrobe: "casual_silk_camisole_denim", talkstyle: "warm_witty_banter", colour: "fuji_eterna_soft", music: "ethereal_shoegaze_dream_95", motion: "slow", energy: "calm", expression: "natural", expr_read: "warm", life: "alive" } },
    { id: "__builtin_kdrama_subway_rain_walk", label: "SFW K-Drama: Neon Alley Rain Walk & Look-Back", values: { style: "korean_drama_glow", camera: "steadicam_follow", place: "neon_night_street", light: "neon_rain_window_caustics", colour: "colour_cinestill_800t_halation", wardrobe: "street_cropped_jacket_cargo", talkstyle: "natural_conversational", ambience: "rain_heavy", music: "piano_cello_65", motion: "natural", energy: "steady", expression: "natural", expr_read: "warm", life: "alive" } },
    { id: "__builtin_loft_studio_vlog_host", label: "SFW Everyday: Sunlit Artist Loft Camera Vlog", values: { style: "h3_astro_cinema", camera: "push_in", place: "sunlit_loft_studio", light: "soft_natural_light", colour: "colour_kodak_portra_400_warm", wardrobe: "casual_silk_camisole_denim", talkstyle: "bright_vlog_host", ambience: "room_tone", music: "city_pop_80s_112", motion: "natural", energy: "charged", expression: "vivid", expr_read: "warm", life: "alive" } },
    { id: "__builtin_scifi_starship_standoff", label: "SFW Sci-Fi Thriller: Orbital Observation Deck Briefing", values: { style: "h3_astro_cinema", camera: "dolly_push_to_ecu_eyes", place: "starship_observation_deck", light: "chiaroscuro_hard_slash", colour: "teal_orange", wardrobe: "street_cyberpunk_holo_jacket_straps", talkstyle: "calm_tactical_briefing", music: "dark_cello_thriller_pulse_90", motion: "slow", energy: "steady", expression: "stoic", expr_read: "tense", life: "natural" } },
    { id: "__builtin_douyin_kemusan_neon_street_916", label: "SFW Douyin Trend: Kemusan (科目三) Street-Snap Neon Dance (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", camera: "cam_handheld_vertical_dance_follow", pose: "dance_douyin_subject_three_kemusan,dance_douyin_slowmo_street_strut_wink", place: "neon_night_street", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", wardrobe: "street_cropped_jacket_cargo", music: "city_pop_80s_112", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_douyin_guofeng_bamboo_fan_916", label: "SFW Douyin Guofeng: Moonlit Bamboo Silk-Fan Spin Dance (9:16)", values: { style: "wuxia_wirefu_cinema", camera: "cam_idol_low_angle_pedestal_rise", pose: "dance_douyin_guofeng_sleeve_fan_snap", place: "plate_snowy_bamboo_forest_moonlight", light: "moonlight", colour: "emerald_anime_midnight", wardrobe: "action_traditional_samurai_kimono_slit", music: "taiko_war_drums_138", motion: "brisk", energy: "steady", expression: "vivid", expr_read: "stoic", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_tiktok_espresso_paparazzi_916", label: "SFW TikTok Viral: Espresso Breezy Groove + 2000s Paparazzi Flash (9:16)", values: { style: "viral_2000s_paparazzi_flash", camera: "cam_beat_snap_micro_push", pose: "dance_tiktok_espresso_breezy_step,dance_tiktok_camera_tap_transition", place: "plate_mirror_dance_rehearsal_studio", light: "editorial_softbox_beauty_key", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", music: "french_touch_filter_house_120", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_916_pov_intimate", label: "9:16 First-Person POV + Warm Intimate", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", place: "penthouse_silk_bedroom", light: "vip_amber_booth", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", pov: "male", talk_mode: "auto" } },
    { id: "__builtin_anime_to_real", label: "2D Anime -> Photoreal Transition (1->2)", values: { style: "h3_sakuga_2d,h3_astro_cinema", dial_modes: { style: "sequence" }, camera: "orbit_push", place: "neon_night_street", light: "neon_rain_window_caustics", colour: "teal_orange", motion: "brisk", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_neon_cyber_action", label: "Neon Cyberpunk + Action Combo", values: { style: "cyberpunk_edgerunners_neon", camera: "whip_pan_reaction_match", place: "tokyo_neon_rain_rooftop", light: "cyber_dual_gel", colour: "teal_orange", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_slow_sensual_purr", label: "Slow Sensual Tease (Hushed Energy + Soft Breath)", values: { style: "glamour_boudoir_8k", camera: "dolly_push_to_ecu_eyes", place: "penthouse_silk_bedroom", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", motion: "slow", energy: "hush", expression: "subtle", expr_read: "sensual", life: "natural", talk_mode: "auto" } },
    { id: "__builtin_3cut_morning_suite_916", label: "NSFW 3-Cut Morning Suite: Oral -> Glass Shower -> Vanity Mirror (9:16)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", place: "penthouse_silk_bedroom", explicit: "multi_pos_3cut_morning_bed_shower_vanity", wardrobe: "nude_full", light: "soft_natural_light", colour: "champagne_honey_glow", ambience: "bathhouse_steam_water_drip", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_3cut_office_trilogy_916", label: "NSFW 3-Cut Office Trilogy: Under-Desk -> Chair Spin -> Skyline Glass (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "multi_position_3cut_intimate", explicit: "multi_pos_office_under_desk_to_chair_spin_to_glass_wall", place: "executive_corner_office_midnight", wardrobe: "fetish_office_siren_skirt", light: "sunset_blinds_gold", colour: "champagne_honey_glow", ambience: "penthouse_night_hum", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_mirror_vertical_doggy", label: "9:16 Vanity Mirror Doggy + Warm Candlelight", values: { style: "glamour_boudoir_8k", explicit: "standing_mirror_vanity_doggy", camera: "mirror_three_way_reflection", place: "plate_penthouse_master_bed_mirror", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", ambience: "intimate_skin_foley", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_kpop_dance_3angle", label: "K-Pop Idol 3-Angle Dance Cut + UV Stage Haze", values: { style: "style_kpop_music_bank_4k_stage", camera: "multi_angle_action_close", pose: "dance_kpop_chest_pop_body_wave,dance_gravure_s_curve_hip_roll", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "street_idol_stage_coord_blazer_mini", light: "strip_club_uv_blacklight_laser_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_girl_crush_bass_drop_124", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_penthouse_rain_silent", label: "Penthouse Midnight Rain + Candlelight Whisper (Silent)", values: { style: "h3_astro_cinema", camera: "push_in", place: "plate_luxury_rooftop_infinity_pool", light: "candlelight_and_moonlight_split", colour: "kodak_vision3_500t", ambience: "tokyo_love_hotel_rain_hum", music: "bedroom_lofi_rain_64", motion: "slow", energy: "hush", expression: "subtle", expr_read: "warm", life: "natural", talk_mode: "silent" } },
    { id: "__builtin_editorial_flash_glamour", label: "Editorial 35mm Flash Fashion Slow-Mo Glamour", values: { style: "editorial_vogue_flash_cinema", light: "editorial_softbox_beauty_key", camera: "dolly_push_to_ecu_eyes", place: "plate_white_cube_art_gallery", colour: "colour_kodak_portra_400_warm", wardrobe: "glam_champagne_bias_slip_dress", music: "city_pop_80s_112", motion: "slow", energy: "steady", expression: "natural", expr_read: "stoic", life: "natural", talk_mode: "silent" } },
    { id: "__builtin_anime2real_water_dragon", label: "Anime2Real Water Dragon + Neon Rain Street vs Goons", values: { style: "anime2real_live_action_vfx", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "combat_anime2real_water_breathing_dragon", fx: "vfx_anime2real_water_dragon_slash", fx_timing: "from_start", place: "plate_shibuya_rain_crosswalk_crater", light: "anime2real_elemental_aura_interactive_key", colour: "ufotable_neon_hdr_contrast", wardrobe: "anime2real_demon_slayer_haori_corps", music: "ufotable_orchestral_taiko_choir_140", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_anime2real_mixed_2d_ink", label: "Mixed-Reality 2D Cel-Slash + Photoreal Brawler", values: { style: "anime2real_live_action_vfx", camera: "multi_angle_action_close", combat: "combat_anime2real_2d_ink_manga_mixed_reality", fx: "vfx_anime2real_2d_cel_slash_ribbons", fx_timing: "from_start", place: "tokyo_neon_rain_rooftop", light: "anime_cel_hard_rim", colour: "ufotable_neon_hdr_contrast", wardrobe: "street_cropped_jacket_cargo", music: "sakuga_anime_rock_165", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_one_take_cowgirl_transition", label: "One Continuous Take: Thong Aside -> Cowgirl Sink & Bounce", values: { style: "glamour_boudoir_8k", camera: "body_contour_s_curve_pedestal_glide", place: "penthouse_silk_bedroom", explicit: "cont_panties_aside_rub_to_cowgirl_sink_to_grind", wardrobe: "partial_panties_pulled_aside", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_one_take_deepthroat_facial", label: "One Continuous Take: Handjob & Lick -> Deepthroat -> Facial", values: { style: "glamour_boudoir_8k", explicit: "cont_handjob_lick_to_deepthroat_to_swallow", camera: "portrait_vertical_stack", place: "penthouse_silk_bedroom", light: "vip_amber_booth", colour: "champagne_honey_glow", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_gravure_idol_s_curve_dance", label: "4K Gravure Idol S-Curve Dance + Body-Contour Pedestal", values: { style: "japanese_4k_gravure_idol_cinema", camera: "body_contour_s_curve_pedestal_glide", pose: "dance_gravure_s_curve_hip_roll,dance_kpop_chest_pop_body_wave", place: "minimal_cyclorama_set", wardrobe: "swim_cutout_white_monokini_gold_rings", light: "tokyo_love_hotel_magenta_violet_velvet", colour: "peach_milk_gravure", music: "city_pop_80s_112", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_ensemble_s1_s9_cypher_squad", label: "Multi-Character Ensemble (S1-S9): V-Formation + 360 Cypher Orbit", values: { style: "style_kpop_music_bank_4k_stage", camera: "ensemble_360_cypher_orbit_s1_s9", pose: "ensemble_v_formation_idol_squad_s1_s9", lens: "comp_ensemble_s1_s9_depth_stagger", place: "plate_proscenium_theater_stage_spotlight", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_girl_crush_bass_drop_124", motion: "brisk", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_anime2real_senbonzakura_storm", label: "Anime2Real Bankai Senbonzakura Blade-Petal Storm", values: { style: "anime2real_live_action_vfx", camera: "orbit_360", combat: "combat_anime2real_senbonzakura_cherry_blossom_blade_storm", fx: "vfx_anime2real_senbonzakura_petal_vortex", fx_timing: "from_start", place: "plate_anime2real_soul_society_cherry_blossom_courtyard", light: "anime2real_elemental_aura_interactive_key", wardrobe: "anime2real_bleach_shihakusho_open_chest_zanpakuto", colour: "ufotable_neon_hdr_contrast", music: "ufotable_orchestral_taiko_choir_140", motion: "brisk", energy: "peak", expression: "stoic", expr_read: "stoic", life: "hyper" } },
    { id: "__builtin_anime2real_sandevistan_blitz", label: "Anime2Real Cyberpunk Sandevistan Afterimage Blitz", values: { style: "anime2real_live_action_vfx", combat: "combat_anime2real_sandevistan_afterimage_time_freeze_blitz", fx: "vfx_anime2real_sandevistan_afterimage_ribbon", fx_timing: "from_start", camera: "sandevistan_freeze_orbit_180", place: "tokyo_neon_rain_rooftop", light: "cyber_dual_gel", wardrobe: "street_cyberpunk_holo_jacket_straps", colour: "emerald_matrix_gunmetal", music: "cyberpunk_edgerunner_hyper_synth_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_fetish_femdom_leash_worship", label: "Playbook: Collar & Leash Petplay -> Boot Worship -> Facesit", values: { style: "erotic_thriller_90s_35mm", camera: "low_angle_power_pedestal", place: "bdsm_red_dungeon_cross", light: "red_velvet_boudoir", colour: "crimson_john_wick_gold", explicit: "cont_femdom_leash_crawl_to_boot_lick_to_facesit_smother", fetish: "collar_leash_petplay_walk,foot_domination", wardrobe: "fetish_latex_catsuit_unzipped", talkstyle: "velvet_hypnotic_domme_count", motion: "slow", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive" } },
    { id: "__builtin_under_desk_secret_to_cowgirl", label: "Secret Under-Desk Stroke & Deepthroat -> Executive Lap Cowgirl", values: { style: "erotic_thriller_90s_35mm", camera: "portrait_vertical_stack", explicit: "cont_under_desk_two_hand_stroke_to_deepthroat_to_lap_cowgirl", fetish: "office_under_desk_secret", place: "plate_executive_boardroom_under_mahogany_table", light: "sunset_blinds_gold", colour: "champagne_honey_glow", wardrobe: "fetish_office_siren_skirt", talkstyle: "secretive_office_whisper", motion: "natural", energy: "hush", expression: "vivid", expr_read: "sly", life: "alive" } },
    { id: "__builtin_s1_vs_s2_katana_rain_duel", label: "S1 vs S2: Rainy Lantern Alley Katana Sparks Duel", values: { style: "john_wick_neon_gunfu", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "combat_s1_s2_mirror_blade_duel", fx: "vfx_sword_spark_shower", fx_timing: "from_start", place: "plate_rainy_chinatown_lantern_alley", wardrobe: "anime2real_open_silk_kimono_katana", light: "rain_neon_puddle_bounce", colour: "crimson_john_wick_gold", ambience: "neon_alley_puddle_footsteps", music: "taiko_war_drums_138", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_s1_s2_tag_team_corridor_clear", label: "S1 + S2 Tag-Team: Corridor Sweep -> Vault Flying Knee Brawl", values: { style: "john_wick_neon_gunfu", combat: "combat_s1_s2_tag_team_combo_finisher", camera: "track_side", place: "shattered_marble_lobby", wardrobe: "action_stealth_infiltration_turtleneck_harness", light: "cyber_dual_gel", colour: "teal_orange", fx: "vfx_kinetic_shockwave_dust_ring", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_parkour_table_slide_gunfu", label: "Parkour Gun-Fu: Boardroom Table Slide & Brass Rain", values: { style: "john_wick_neon_gunfu", combat: "combat_env_table_slide_gun_sweep", fx: "vfx_muzzle_brass_storm", fx_timing: "from_start", place: "plate_executive_boardroom_glass_table", light: "chiaroscuro_hard_slash", colour: "crimson_john_wick_gold", wardrobe: "tailored_black_blazer_trousers", camera: "whip_pan_reaction_match", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_anime2real_domain_void_shrine", label: "Anime2Real: Domain Shrine Fracture & Crimson Slashes", values: { style: "anime2real_live_action_vfx", camera: "orbit_push", combat: "combat_anime2real_domain_void_shrine_cut", fx: "vfx_crimson_lightning_black_sparks", fx_timing: "from_start", place: "plate_shibuya_rain_crosswalk_crater", light: "anime2real_elemental_aura_interactive_key", colour: "emerald_anime_midnight", wardrobe: "anime2real_jjk_sorcerer_high_collar", music: "anime_orchestral_choir_148", motion: "slow", energy: "peak", expression: "stoic", expr_read: "stoic", life: "hyper" } },
    { id: "__builtin_wuxia_moonlit_bamboo_swordplay", label: "90s Wuxia Cinema: Moonlit Snowy Bamboo Jian Duel", values: { style: "wuxia_wirefu_cinema", camera: "arc_left", combat: "combat_s1_s2_sword_vs_barehand_catch", place: "plate_snowy_bamboo_forest_moonlight", light: "moonlight", wardrobe: "action_traditional_samurai_kimono_slit", colour: "emerald_anime_midnight", ambience: "dojo_wood_creak_wind", music: "taiko_war_drums_138", motion: "brisk", energy: "charged", expression: "stoic", expr_read: "intense", life: "hyper" } },
    { id: "__builtin_bdsm_shibari_candlelit_wall", label: "BDSM Shibari: Crimson Rope Chest Harness + Fireplace Chalet", values: { style: "glamour_boudoir_8k", camera: "pedestal_up", explicit: "bdsm_shibari_chest_harness_wall_tie", fetish: "shibari_rope_chest_diamonds", wardrobe: "fetish_shibari_crimson_rope_harness", place: "plate_satin_four_poster_fireplace_cabin", light: "fireplace_ember_warm_low", colour: "champagne_honey_glow", ambience: "fireplace_ember_pop_silk", motion: "slow", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_lesbian_steamy_shower_duo", label: "Steamy Shower: Wet Glass Press & Two-Subject Embrace", values: { style: "glamour_boudoir_8k", camera: "push_in", explicit: "lesbian_standing_shower_breast_press_thigh_ride", wardrobe: "nude_both_partners", place: "plate_glass_walled_rain_shower_penthouse", light: "soft_natural_window", colour: "champagne_honey_glow", fx: "fx_steam_mirror_condensation_clear", fx_timing: "from_start", ambience: "bathhouse_steam_water_drip", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_pegging_dominant_harness_bed", label: "Domme Pegging: Leather Harness Strap-On Doggy", values: { style: "glamour_boudoir_8k", camera: "low_angle_power_pedestal", explicit: "cont_strapon_harness_buckle_to_pegging_doggy", fetish: "pegging,strap_on", wardrobe: "fetish_strapon_harness_nude", place: "penthouse_silk_bedroom", light: "red_velvet_boudoir", colour: "crimson_john_wick_gold", ambience: "intimate_skin_foley", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_90s_erotic_thriller_noir", label: "90s Erotic Thriller: Venetian Blinds Noir Office Dialogue", values: { style: "erotic_thriller_90s_35mm", camera: "ots_talk", place: "executive_corner_office_midnight", light: "sunset_blinds_gold", wardrobe: "fetish_office_siren_skirt", talkstyle: "husky_velvet", music: "sultry_jazz_noir_sax_72", colour: "champagne_honey_glow", motion: "slow", energy: "calm", expression: "natural", expr_read: "sly", life: "natural" } },
    { id: "__builtin_yacht_sunset_continuous_take", label: "Luxury Superyacht Sunset: Swimsuit Climb-Out -> Wet Missionary", values: { style: "glamour_boudoir_8k", camera: "arc_right", explicit: "cont_pool_edge_climb_out_to_wet_missionary", fetish: "yacht_sunpad_ocean_wind", place: "plate_superyacht_aft_sunpad_mediterranean", wardrobe: "partial_bikini_strings_untied_hanging", light: "sunset_silhouette_halo_rim", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_candlelit_aftercare_whisper", label: "Post-Climax Aftercare: Alpine Fireplace Cuddle & Husky Murmur", values: { style: "h3_astro_cinema", camera: "static_close", fetish: "aftercare_cuddle_pillow_talk", place: "plate_satin_four_poster_fireplace_cabin", wardrobe: "partial_silk_robe_open_front", light: "fireplace_ember_warm_low", colour: "champagne_honey_glow", talkstyle: "husky_aftercare_murmur", ambience: "fireplace_ember_pop_silk", music: "ethereal_shoegaze_dream_95", motion: "freeze", energy: "hush", expression: "subtle", expr_read: "warm", life: "natural" } },
    { id: "__builtin_switch_banter_displaced_lace", label: "Switch Banter & Displaced Lace (9:16 Continuous)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "cont_panties_aside_rub_to_cowgirl_sink_to_grind", wardrobe: "partial_panties_pulled_aside", place: "plate_penthouse_master_bed_mirror", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", talkstyle: "switch_power_reversal_tease", ambience: "intimate_skin_foley", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sly", life: "alive" } },
    { id: "__builtin_shower_glass_press_lift_916", label: "Steamy Shower Glass Press -> Standing Lift (9:16 One Take)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "cont_shower_glass_press_to_standing_carry", fetish: "glass_press_shower_window", wardrobe: "nude_wet_shower", place: "plate_glass_walled_rain_shower_penthouse", light: "soft_natural_window", colour: "champagne_honey_glow", fx: "fx_steam_mirror_condensation_clear", fx_timing: "from_start", talkstyle: "pillow_giggle_banter", ambience: "bathhouse_steam_water_drip", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive" } },
    { id: "__builtin_car_backseat_fogged_916", label: "Rainy Car Backseat Fogged Window Straddle (9:16 Hushed)", values: { style: "erotic_thriller_90s_35mm", camera: "portrait_vertical_stack", explicit: "cont_car_backseat_fogged_glass_straddle_to_climax", place: "plate_rain_car_backseat_city_lights", wardrobe: "partial_dress_hiked_waist", light: "rain_neon_puddle_bounce", colour: "kodak_vision3_500t", talkstyle: "risk_adrenaline_hush", ambience: "rain_thunder_window_glass", motion: "natural", energy: "hush", expression: "vivid", expr_read: "sensual", life: "alive" } },
    { id: "__builtin_desk_spin_ledger_169", label: "Executive Desk Chair Spin -> Bent-Over Ledger (16:9)", values: { style: "erotic_thriller_90s_35mm", camera: "orbit_push", explicit: "cont_desk_chair_spin_to_bent_over_ledger", place: "executive_corner_office_midnight", wardrobe: "fetish_office_siren_skirt", light: "sunset_blinds_gold", colour: "champagne_honey_glow", talkstyle: "cocky_dominant_commentary", ambience: "penthouse_night_hum", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive" } },
    { id: "__builtin_tiktok_water_mirror_dance_916", label: "TikTok 'Water' Hip-Shake + Ending Fairy Mirror Studio (9:16)", values: { style: "korean_drama_glow", camera: "cam_handheld_vertical_dance_follow", pose: "dance_tiktok_water_hip_shake_hair_sweep,dance_kpop_ending_fairy_breath_hair_tuck", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", light: "strip_club_uv_blacklight_laser_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_girl_crush_bass_drop_124", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_kpop_sticky_arch_heels_uv_916", label: "K-Pop Sultry Arch + Heels Kick Club Flow (9:16)", values: { style: "japanese_4k_gravure_idol_cinema", camera: "cam_contour_shoulder_hip_glide", pose: "dance_kpop_sticky_arch_hip_sway_wink,dance_kpop_heels_kick_plant_hip_sway", place: "neon_strip_club_pole", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "club_laser_strobe_haze", colour: "peach_milk_gravure", music: "club_house_124", motion: "brisk", energy: "peak", expression: "vivid", expr_read: "sensual", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_tiktok_bedroom_siren_cozy_916", label: "TikTok Cozy Hoodie Bedroom Bounce + Siren Eyes (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", camera: "cam_beat_snap_micro_push", pose: "dance_tiktok_cozy_bedroom_pajama_heart,dance_tiktok_siren_eyes_collarbone_lip_bite", wardrobe: "street_oversized_boyfriend_hoodie_bare_legs", place: "plate_penthouse_master_bed_mirror", light: "candlelight_flicker_boudoir", colour: "peach_milk_gravure", music: "dark_rnb_sub_bass_68", motion: "slow", energy: "calm", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_tiktok_mirror_sync_169", label: "Duet Mirror Rehearsal: Synced Step-Touch, Spin & Laugh (16:9)", values: { style: "style_commercial_beauty_skincare_reel", camera: "cam_beat_drop_punch_wide_combo", pose: "dance_duet_kpop_mirror_studio_rehearsal", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "street_varsity_bomber_parachute_pants", light: "bathroom_vanity_mirror_bulbs", colour: "colour_kpop_pastel_milk_highlights", music: "french_touch_filter_house_120", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_club_pole_twerk_heels_916", label: "Club Brass Pole 360 Spin -> Wall Squat Twerk (9:16)", values: { style: "japanese_4k_gravure_idol_cinema", camera: "cam_low_hero_squat_to_highkick_boom", pose: "dance_pole_orbit_spin_slow_slide,dance_wall_squat_twerk_glance", place: "neon_strip_club_pole", wardrobe: "glam_sequined_champagne_fringe_mini", light: "strip_club_uv_blacklight_laser_haze", colour: "peach_milk_gravure", music: "dark_velvet_weeknd_synth_rnb_75", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_elevator_coat_flash_rear_916", label: "Mirrored Elevator Trench-Coat Flash -> Rear Entry (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "mirror_three_way_reflection", explicit: "cont_elevator_coat_flash_to_mirror_rear_entry", fetish: "elevator_risk_door_closed", place: "plate_glass_elevator_skyline_shaft", wardrobe: "partial_skirt_bunched_hips", light: "vip_amber_booth", colour: "kodak_vision3_500t", talkstyle: "risk_adrenaline_hush", motion: "natural", energy: "hush", expression: "vivid", expr_read: "sensual", life: "alive" } },
    { id: "__builtin_morning_sunbeam_cowgirl_916", label: "Sunlit Morning Linen Wake-Up -> Lazy Chest-to-Chest Cowgirl (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "cont_morning_stretch_under_duvet_to_lazy_cowgirl", fetish: "morning_wake_up_somno_tease", place: "penthouse_silk_bedroom", light: "soft_natural_window", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", motion: "slow", energy: "calm", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_female_pov_missionary_916", label: "Female POV Looking Up: Intense Missionary Eye-Lock (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "pov_female_looking_up_missionary", place: "penthouse_silk_bedroom", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", pov: "female", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_sf_diner_midnight_confession_169", label: "SFW Cinema: Midnight Chrome Diner Quiet Confession (16:9)", values: { style: "h3_astro_cinema", camera: "table_two_shot_profile_to_single", place: "plate_retro_chrome_diner_booth", wardrobe: "street_belted_trench_monochrome_knit", pose: "pose_cafe_table_chin_prop_smile", light: "neon_rain_window_caustics", colour: "kodak_vision3_500t", talkstyle: "earnest_dramatic_confession", motion: "slow", energy: "calm", expression: "natural", expr_read: "warm", life: "natural" } },
    { id: "__builtin_sf_oldtown_walk_and_talk_169", label: "SFW Drama: Blue-Hour Cobblestone Walk & Talk (16:9)", values: { style: "h3_astro_cinema", camera: "steadicam_follow", place: "plate_european_cobblestone_alley_bluehour", wardrobe: "everyday_turtleneck_midi_skirt_boots", pose: "pose_two_shot_walk_and_talk_stop", light: "blue_hour", colour: "fuji_eterna_soft", talkstyle: "warm_witty_banter", motion: "natural", energy: "steady", expression: "natural", expr_read: "warm", life: "alive" } },
    { id: "__builtin_sf_mediterranean_bachata_golden_916", label: "SFW Dance: Mediterranean Cliffside Bachata Sway (9:16)", values: { style: "h3_astro_cinema", camera: "cam_contour_shoulder_hip_glide", place: "plate_mediterranean_cliff_promenade", wardrobe: "everyday_flowing_chiffon_sundress", pose: "dance_latin_bachata_sensual_sway", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "bossa_nova_sunset_88", motion: "natural", energy: "charged", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_sf_laundromat_shuffle_neon_916", label: "SFW Street Dance: 24h Neon Laundromat Shuffle (9:16)", values: { style: "korean_drama_glow", camera: "cam_handheld_vertical_dance_follow", place: "plate_24h_neon_laundromat_midnight", wardrobe: "street_varsity_bomber_parachute_pants", pose: "dance_street_shuffle_cutting_shapes", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", music: "french_touch_filter_house_120", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_sf_boxing_gym_heavy_bag_169", label: "SFW Action: Urban Boxing Gym Heavy-Bag Combo (16:9)", values: { style: "h3_astro_cinema", camera: "track_side", place: "plate_boxing_gym_ring_sunlight", wardrobe: "athletic_boxer_satin_robe_ring_kit", combat: "action_gym_heavy_bag_combo_sweat", light: "soft_natural_window", colour: "kodak_vision3_500t", ambience: "amb_boxing_gym_heavy_bag_chains", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_sf_heist_laser_grid_infiltration_169", label: "SFW Thriller: Vault Laser-Grid Limbo Infiltration (16:9)", values: { style: "h3_astro_cinema", camera: "low_angle_dutch_power_walk", place: "laser_heist_vault_corridor", wardrobe: "action_stealth_infiltration_turtleneck_harness", combat: "action_heist_laser_grid_limbo_weave", light: "cyber_dual_gel", colour: "teal_orange", music: "dark_cello_thriller_pulse_90", motion: "slow", energy: "charged", expression: "stoic", expr_read: "tense", life: "natural", talk_mode: "silent" } },
    { id: "__builtin_sf_tango_theater_spotlight_169", label: "SFW Performance: Theater Stage Argentine Tango Duet (16:9)", values: { style: "h3_astro_cinema", camera: "arc_right", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "glam_crimson_halter_backless_slit_gown", pose: "dance_tango_duet_ocho_leg_hook", light: "chiaroscuro_hard_slash", colour: "crimson_john_wick_gold", music: "sultry_jazz_noir_sax_72", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "intense", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_sf_rooftop_drift_car_169", label: "SFW Stunt: Rooftop Parking Deck Handbrake Drift (16:9)", values: { style: "h3_astro_cinema", camera: "car_chasing_pursuit", place: "plate_concrete_rooftop_parking_golden", wardrobe: "street_cropped_jacket_cargo", combat: "action_car_jturn_handbrake_drift", light: "sunset_silhouette_halo_rim", colour: "teal_orange", music: "drift_phonk_cowbell_135", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_nsfw_limo_3stage_straddle_916", label: "NSFW 3-Stage: Limo Backseat Neon Strip & Lap Straddle (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "multi_position_3cut_intimate", explicit: "stage_car_cabin_3cut_tease_straddle", place: "plate_backseat_luxury_limo_neon", wardrobe: "partial_dress_hiked_waist", light: "neon_rain_window_caustics", colour: "champagne_honey_glow", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_nsfw_yacht_ladder_sunpad_169", label: "NSFW 3-Stage: Yacht Ladder Emergence -> Sunpad Ride (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_pool_ladder_wet_to_sunpad_ride", place: "plate_superyacht_aft_sunpad_mediterranean", wardrobe: "partial_bikini_strings_untied_hanging", light: "sunset_silhouette_halo_rim", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_douyin_girl_sweet_neon_916", label: "SFW Douyin Girl: Cheek-Poke Hip Pop + High-Gloss Neon Beauty (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_douyin_sweet_cheek_poke_hip_pop,dance_douyin_jacket_zip_drop_body_roll", camera: "cam_beat_snap_micro_push", place: "plate_tokyo_izakaya_lantern_alley", wardrobe: "street_idol_stage_coord_blazer_mini", light: "light_ring_beauty_plus_neon_rim", colour: "colour_douyin_porcelain_neon_cyan", music: "city_pop_80s_112", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_tiktok_girl_duet_sync_916", label: "SFW TikTok Girl Duet: Synced Hip-Pop & Relay + Amapiano (9:16)", values: { style: "style_y2k_digicam_direct_flash", pose: "dance_duet_girls_tiktok_sync_hip_clap,dance_duet_girls_tiktok_relay_walkin_pop", camera: "cam_handheld_vertical_dance_follow", place: "plate_24h_neon_laundromat_midnight", wardrobe: "street_varsity_bomber_parachute_pants", light: "neon_rain_window_caustics", colour: "colour_kpop_pastel_milk_highlights", music: "amapiano_logdrum_groove_112", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_sensual_velvet_916", label: "SFW Sensual K-Pop: Collarbone Wave + Rear Figure-8 Glance (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_kpop_sensual_slow_neck_collar_wave,dance_kpop_sensual_rear_figure8_glance", camera: "cam_contour_shoulder_hip_glide", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "slow", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_kpop_sensual_duet_stage_169", label: "SFW Sensual K-Pop Duet: Synced Ribcage Isolation + 360 Orbit (16:9)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_kpop_sensual_duet_mirror_back_arch", camera: "cam_360_slowmo_duet_orbit", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_wong_kar_wai_hk_alley_169", label: "SFW Arthouse: Wong Kar-wai Hong Kong Neon Alley & Cantonese (16:9)", values: { style: "style_wong_kar_wai_neon_stepprint", camera: "steadicam_follow", place: "plate_rainy_chinatown_lantern_alley", light: "rain_neon_puddle_bounce", colour: "colour_cinestill_800t_halation", wardrobe: "everyday_turtleneck_midi_skirt_boots", accent: "cantonese_native_hk", talkstyle: "earnest_dramatic_confession", motion: "slow", energy: "calm", expression: "subtle", expr_read: "warm", life: "natural" } },
    { id: "__builtin_nsfw_mirror_reverse_to_doggy_916", label: "NSFW Continuous Mirror: Reverse Cowgirl -> Pivot Mirror Doggy (9:16)", values: { style: "glamour_boudoir_8k", explicit: "cont_mirror_reverse_cowgirl_to_doggy_flow", camera: "cam_mirror_rack_focus_pull", place: "plate_penthouse_master_bed_mirror", wardrobe: "nude_full", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_douyin_cyber_catwalk_916", label: "SFW Douyin Cyber-Catwalk: Slow-Mo 180° Turn + Ring Neon (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_douyin_cyber_catwalk_slowmo_turn", camera: "cam_idol_low_angle_pedestal_rise", place: "plate_seoul_hongdae_rooftop_bar", wardrobe: "action_cyber_idol_metallic_corset_boots", light: "light_ring_beauty_plus_neon_rim", colour: "colour_douyin_porcelain_neon_cyan", music: "jersey_club_bounce_140", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_tiktok_perreo_girl_duet_916", label: "SFW TikTok Girl Duet: Reggaeton Perreo Sync + Bowling Neon (9:16)", values: { style: "style_y2k_digicam_direct_flash", pose: "dance_duet_girls_tiktok_perreo_mirror_grind", camera: "cam_handheld_vertical_dance_follow", place: "plate_midnight_bowling_alley_neon", wardrobe: "street_y2k_velour_tracksuit_babytee", light: "light_ring_beauty_plus_neon_rim", colour: "colour_kpop_pastel_milk_highlights", music: "reggaeton_perreo_dembow_96", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_sensual_side_profile_916", label: "SFW Sensual K-Pop: Side-Profile S-Curve + Velvet Crop (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_kpop_sensual_side_profile_s_curve,dance_kpop_sensual_satin_glove_lip_trace", camera: "cam_contour_shoulder_hip_glide", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "slow", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_paris_cafe_morning_portra_169", label: "SFW Cinema: Paris Café Morning Terrace + Portra 400 (16:9)", values: { style: "h3_astro_cinema", camera: "table_two_shot_profile_to_single", place: "plate_paris_cafe_terrace_morning", wardrobe: "everyday_ribbed_cardigan_pleated_trousers", pose: "pose_cafe_table_chin_prop_smile", light: "light_overcast_editorial_skylight", colour: "colour_kodak_portra_400_warm", accent: "french_native_parisian", talkstyle: "warm_witty_banter", motion: "slow", energy: "calm", expression: "natural", expr_read: "warm", life: "natural" } },
    { id: "__builtin_london_soho_cinestill_169", label: "SFW Noir: Rainy London Soho Street + CineStill 800T (16:9)", values: { style: "h3_astro_cinema", camera: "steadicam_follow", place: "plate_london_soho_rain_brick_street", light: "rain_neon_puddle_bounce", wardrobe: "street_belted_trench_monochrome_knit", pose: "pose_two_shot_walk_and_talk_stop", colour: "colour_cinestill_800t_halation", accent: "rp_british", talkstyle: "earnest_dramatic_confession", motion: "natural", energy: "steady", expression: "natural", expr_read: "tense", life: "natural" } },
    { id: "__builtin_nsfw_vip_booth_3stage_916", label: "NSFW 3-Stage: Club VIP Booth Lap Grind -> Oral -> Couch Ride (9:16)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", explicit: "stage_vip_booth_3cut_grind_oral_ride", place: "plate_red_velvet_vip_club_booth", wardrobe: "partial_dress_hiked_waist", light: "vip_amber_booth", colour: "champagne_honey_glow", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_nsfw_bedside_69_to_cowgirl_169", label: "NSFW Continuous: Side-Lying 69 -> Roll-Up Cowgirl (16:9)", values: { style: "glamour_boudoir_8k", camera: "push_in", explicit: "cont_bedside_69_flip_to_cowgirl", place: "plate_penthouse_master_bed_mirror", wardrobe: "nude_both_partners", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_nsfw_shower_glass_to_kneel_916", label: "NSFW Continuous Shower: Steamy Glass Kiss -> Kneeling Oral (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "cont_standing_shower_glass_to_kneel_oral", place: "plate_glass_walkin_rainfall_shower", light: "soft_natural_window", colour: "champagne_honey_glow", wardrobe: "nude_wet_shower", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_uber_wick_hallway_gunfu_169", label: "UBER FIGHT (ms): John Wick Hallway Gun-Fu & Knife Disarm (16:9)", values: { style: "john_wick_neon_gunfu", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_wick_hallway_gunfu_knife", place: "shattered_marble_lobby", wardrobe: "action_stealth_infiltration_turtleneck_harness", light: "cyber_dual_gel", colour: "crimson_john_wick_gold", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_wuxia_bamboo_duel_169", label: "UBER FIGHT (ms): Wuxia Bamboo-Canopy Jian Sword Duel (16:9)", values: { style: "wuxia_wirefu_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_wuxia_bamboo_canopy_duel", place: "plate_snowy_bamboo_forest_moonlight", light: "moonlight", colour: "emerald_anime_midnight", wardrobe: "action_traditional_samurai_kimono_slit", music: "taiko_war_drums_138", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_cyberpunk_mantis_169", label: "UBER FIGHT (ms): Cyberpunk Mantis-Blade & Sandevistan Rooftop (16:9)", values: { style: "cyberpunk_edgerunners_neon", camera: "sandevistan_freeze_orbit_180", combat: "uber_fight_cyberpunk_mantis_sandevistan", place: "plate_shibuya_rain_crosswalk_crater", wardrobe: "street_cyberpunk_holo_jacket_straps", light: "cyber_dual_gel", colour: "teal_orange", music: "cyberpunk_edgerunner_hyper_synth_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_mma_cage_ko_169", label: "UBER FIGHT (ms): Championship MMA Cage Counter-Hook to Headkick KO (16:9)", values: { style: "h3_astro_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_mma_counter_headkick_ko", place: "octagon_mma_fight_cage", light: "underground_cage_halide_sweat_rim", colour: "kodak_vision3_500t", wardrobe: "action_mma_fighter_kit", music: "industrial_dark_metal_130", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_split_fashion_walkup_soho_169", label: "SFW Split Wear (S1/S2): NYC SoHo Loft Fashion Walk-Up (16:9)", values: { style: "h3_astro_cinema", camera: "track_back", place: "plate_nyc_soho_cast_iron_loft_window", wardrobe: "glam_champagne_bias_slip_dress,split_partner_black_turtleneck_tailored_trousers", dial_modes: { wardrobe: "split" }, pose: "pose_two_shot_split_wardrobe_walkup", light: "light_golden_hour_dust_slats", colour: "colour_kodak_portra_400_warm", fx: "fx_golden_dust_motes_sunbeam", fx_timing: "from_start", motion: "natural", energy: "steady", expression: "natural", expr_read: "warm", life: "alive" } },
    { id: "__builtin_split_kpop_stage_duet_169", label: "SFW Split Wear (S1/S2): K-Pop Stage Duet + Confetti Sparkle (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_360_slowmo_duet_orbit", place: "plate_proscenium_theater_stage_spotlight", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_kpop_velvet_crop_asymmetric_mini,split_partner_kpop_stage_harness_shirt", dial_modes: { wardrobe: "split" }, pose: "dance_duet_couple_idol_stage_back_embrace", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_sensual_velvet_rnb_98", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_douyin_moonlight_coquette_916", label: "SFW Douyin Girl: Moonlight Hair-Wave + Coquette Ballet Atelier (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", camera: "cam_beat_snap_micro_push", pose: "dance_douyin_moonlight_hair_wave_snap", place: "plate_ballet_rehearsal_sunlit_atelier", light: "soft_natural_window", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", fx: "fx_sakura_petal_wind_drift", fx_timing: "from_start", ambience: "amb_dance_studio_sneaker_squeak", music: "city_pop_80s_112", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_sensual_heels_wall_916", label: "SFW Sensual K-Pop: Back-to-Wall Heel Slide + Hongdae Neon (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_kpop_sensual_heels_wall_slide_arch,dance_kpop_sensual_blindfold_neck_arch", camera: "cam_contour_shoulder_hip_glide", place: "plate_seoul_hongdae_rooftop_bar", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "slow", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_amalfi_lemon_sundress_169", label: "SFW Cinema: Amalfi Lemon Pergola + Flowing Sundress (16:9)", values: { style: "h3_astro_cinema", camera: "push_in", place: "plate_amalfi_lemon_terrace_pergola", light: "golden_hour", wardrobe: "everyday_flowing_chiffon_sundress", pose: "pose_balcony_railing_lean_breeze", colour: "colour_golden_hour_bronze_glow", ambience: "amb_ocean_cliff_surf_breeze", accent: "italian_native_roma", motion: "slow", energy: "calm", expression: "natural", expr_read: "warm", life: "alive" } },
    { id: "__builtin_uber_matrix_lobby_bullet_169", label: "UBER FIGHT (ms): Matrix Marble Lobby Bullet-Time & Pillar Shatter (16:9)", values: { style: "h3_astro_cinema", camera: "sandevistan_freeze_orbit_180", combat: "uber_fight_matrix_lobby_pillar_shatter", place: "shattered_marble_lobby", light: "chiaroscuro_hard_slash", colour: "emerald_matrix_gunmetal", wardrobe: "action_tactical_catsuit", fx: "fx_anamorphic_warm_lens_flare", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_nsfw_sauna_3stage_916", label: "NSFW 3-Stage: Cedar Sauna Steam Rub -> Oral -> Bench Doggy (9:16)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", explicit: "stage_sauna_3cut_steam_bench_to_glass", place: "plate_cedar_sauna_frosted_steam", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", wardrobe: "nude_wet_shower", ambience: "amb_cedar_sauna_hot_stones", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_nsfw_fitting_room_3stage_916", label: "NSFW 3-Stage: Boutique 3-Way Mirror Curtain Peel -> Oral -> Doggy (9:16)", values: { style: "glamour_boudoir_8k", camera: "mirror_three_way_reflection", explicit: "stage_mirror_fitting_room_3cut_curtain_reveal", place: "plate_fitting_room_three_way_mirrors", light: "bathroom_vanity_mirror_bulbs", colour: "champagne_honey_glow", wardrobe: "partial_dress_hiked_waist", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_duet_choochoo_beach_169", label: "🔥 Duet (15s Vision · 4:3/16:9): Stacked V-Lean, L-Guns, Backsteps & Hook-Kick Hang", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_choochoo_hype_train_cuts", camera: "cam_viral_dutch_90roll_wipe_cuts", place: "plate_pacific_wet_sand_sunset_beach", wardrobe: "gold_metallic_bikini_swim", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_whiplash_runway_916", label: "⚡ K-Pop Duet: Whiplash Neck-Snap + Cyber Runway Drop (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_whiplash_necksnap_catwalk", camera: "cam_beat_drop_punch_wide_combo", place: "plate_rainy_backstage_concert_tunnel", wardrobe: "action_cyber_idol_metallic_corset_boots", light: "cyber_dual_gel", colour: "colour_douyin_porcelain_neon_cyan", music: "kpop_whiplash_runway_electro_128", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_sticky_pool_squat_916", label: "🔥 Sexy/Energetic Duet: Sticky Summer Squat-Bounce + Infinity Pool (9:16)", values: { style: "style_commercial_beauty_skincare_reel", pose: "dance_duet_sticky_summer_squat_bounce", camera: "cam_low_hero_squat_to_highkick_boom", place: "plate_desert_villa_infinity_courtyard", wardrobe: "swim_emerald_one_shoulder_cutout", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "amapiano_logdrum_groove_112", motion: "max", energy: "peak", expression: "vivid", expr_read: "sensual", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_addicted_velvet_club_916", label: "💋 Sexy/Fierce Duet: Velvet Club Claw-Reach + Finger-Lip Tease (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_addicted_velvet_claw_tease", camera: "cam_beat_snap_micro_push", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", music: "melodic_afterlife_techno_126", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_arrest_siren_arcade_916", label: "🚨 Cute/Cheeky Duet: Siren Hands + Finger-Gun Arrest Neon Bowling (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_arrest_siren_fingergun", camera: "cam_beat_drop_punch_wide_combo", place: "plate_midnight_bowling_alley_neon", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", light: "light_ring_beauty_plus_neon_rim", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_siren_hyperpop_jersey_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_neon_spin_highkick_916", label: "🦵 K-Pop Duet: NEON Low Vogue -> Spin & Soaring High Kick (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_neon_spin_highkick_drop", camera: "cam_low_hero_squat_to_highkick_boom", place: "plate_marble_museum_rotunda_skylight", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_idol_stage_coord_blazer_mini", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_palm_wipe_hongdae_916", label: "✨ Douyin/TikTok Duet: Palm-Over-Lens Whip Reveal + Hongdae Glow (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_palm_wipe_fit_glow_strut", camera: "cam_palm_cover_lens_reveal_snap", place: "plate_seoul_hongdae_rooftop_bar", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", music: "jersey_club_bounce_140", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_helicopter_latin_169", label: "💃 Sultry/Fiery Duet: Helicopter Hands + Latin K-Pop Sunset Terrace (16:9)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_helicopter_latin_shimmy", camera: "cam_360_slowmo_duet_orbit", place: "plate_amalfi_lemon_terrace_pergola", wardrobe: "glam_sequined_champagne_fringe_mini", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "reggaeton_perreo_dembow_96", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_mirror_canon_party_169", label: "🎉 Party Duet: Mirror Staggered Train-Wave + Confetti Stage (16:9)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_mirror_canon_train_wave", camera: "cam_beat_drop_punch_wide_combo", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "street_balletcore_wrap_bolero_legwarmers", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "club_house_124", motion: "max", energy: "peak", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_y2k_digicam_laundromat_916", label: "📸 Y2K Digicam Duet: Fork-Twirl Wink + Laundromat Flash Squat-Pop (9:16)", values: { style: "style_y2k_digicam_direct_flash", pose: "dance_duet_y2k_digicam_forktwirl_squat", camera: "cam_handheld_vertical_dance_follow", place: "plate_24h_neon_laundromat_midnight", light: "light_ring_beauty_plus_neon_rim", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_y2k_velour_tracksuit_babytee", music: "kpop_y2k_ukgarage_bounce_122", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_choochoo_neon_stage_169", label: "🚂 Hype Train II (Neon Stage · 4:3/16:9): Laser Montage, Backsteps & Hook-Kick Hang", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_choochoo_hype_train_cuts", camera: "cam_viral_dutch_90roll_wipe_cuts", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "action_cyber_idol_metallic_corset_boots", light: "light_kpop_concert_multi_spot_haze", colour: "colour_douyin_porcelain_neon_cyan", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_guofeng_sakura_916", label: "🌸 Douyin Guofeng Duet: Bamboo Shrine Sleeve-Wave + Sakura Trap (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_guofeng_sleeve_snap_trap", camera: "cam_beat_drop_punch_wide_combo", place: "plate_kyoto_bamboo_shrine_stone_steps", light: "moonlight", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", fx: "fx_sakura_petal_wind_drift", fx_timing: "from_start", music: "douyin_guofeng_guzheng_trap_92", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_baile_funk_pool_916", label: "🌙 Baile Funk Duet: Night Skyline Infinity Pool Squat & Sway (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_baile_funk_pool_squat_sizzle", camera: "cam_low_hero_squat_to_highkick_boom", place: "plate_rooftop_infinity_pool_skyline", wardrobe: "swim_cutout_white_monokini_gold_rings", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", music: "baile_funk_tambor_130", motion: "max", energy: "peak", expression: "vivid", expr_read: "sensual", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_elevator_mirror_glam_916", label: "🥂 Luxury Lift Duet: Smoked-Mirror Rack-Focus + Chainmail Dress (9:16)", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_duet_elevator_mirror_door_sway", camera: "cam_mirror_rack_focus_pull", place: "plate_luxury_champagne_private_elevator", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "vip_amber_booth", colour: "champagne_honey_glow", music: "kpop_sensual_velvet_rnb_98", motion: "slow", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_tokyo_ramen_jersey_916", label: "🍜 Midnight Tokyo Rain Duet: Neon Ramen Jersey-Club Bounce (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_jersey_triplet_hop_puddle", camera: "cam_handheld_vertical_dance_follow", place: "plate_neon_cyber_ramen_shop_rain", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", wardrobe: "street_cargo_miniskirt_zip_hoodie_platforms", fx: "fx_raindrop_on_camera_glass", fx_timing: "from_start", music: "jersey_club_bounce_140", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_greenhouse_coquette_916", label: "🌿 Glasshouse Coquette Duet: Cheek-Poke + Fairy-Light Spin (9:16)", values: { style: "style_commercial_beauty_skincare_reel", pose: "dance_duet_coquette_cheekpoke_spin_flare", camera: "cam_beat_snap_micro_push", place: "plate_rooftop_greenhouse_botanical_night", light: "practical", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "natural", energy: "charged", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_parking_afrobeats_169", label: "🌅 Golden Parking-Deck Duet: 360° Sunset Orbit Afrobeats (16:9)", values: { style: "style_commercial_beauty_skincare_reel", pose: "dance_duet_afrobeats_360_shoulder_groove", camera: "cam_360_slowmo_duet_orbit", place: "plate_concrete_rooftop_parking_golden", wardrobe: "everyday_oversized_poplin_shirt_bike_shorts", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "afrobeats_warm_pluck_106", motion: "natural", energy: "steady", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_duet_hi8_vinyl_916", label: "📼 90s Hi8 Vinyl Shop Duet: Crate-Peek Pop + UK Garage Two-Step (9:16)", values: { style: "style_90s_hi8_camcorder_night", pose: "dance_duet_vinyl_aisle_two_step_peek", camera: "cam_handheld_vertical_dance_follow", place: "plate_vinyl_record_shop_aisles", light: "practical", colour: "kodak_vision3_500t", wardrobe: "everyday_90s_denim_jacket_straight_jeans", music: "kpop_y2k_ukgarage_bounce_122", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_simple_natural_bedroom_solo_916", label: "🛏️ Simple Enclosed Bedroom (Soft Natural Ambient, Solid Walls): Cozy Groove (9:16)", values: { style: "h3_astro_cinema", camera: "cam_beat_snap_micro_push", place: "plate_simple_enclosed_soft_natural_bedroom", light: "soft_natural_light", colour: "colour_kodak_portra_400_warm", pose: "dance_tiktok_cozy_bedroom_pajama_heart,dance_gravure_s_curve_hip_roll", wardrobe: "street_oversized_boyfriend_hoodie_bare_legs", music: "city_pop_80s_112", motion: "natural", energy: "steady", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_solo_waacking_crunk_neon_916", label: "⚡ Energy Solo: Arm Waacking, Reverse Backsteps & Hook-Kick Hang (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_solo_waacking_crunk_hook_kick_12s", camera: "cam_distant_wide_master_to_hardcut_closeup", place: "plate_tokyo_izakaya_lantern_alley", wardrobe: "street_idol_stage_coord_blazer_mini", light: "neon_rain_window_caustics", colour: "colour_douyin_porcelain_neon_cyan", music: "kpop_crunk_waacking_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_house_jack_backstep_169", label: "🔥 Energy Duet: Stacked V-Lean -> Same-Dir Backsteps + House Jack (16:9)", values: { style: "style_commercial_beauty_skincare_reel", pose: "dance_duet_stacked_v_lean_popping_microfreeze,dance_duet_same_dir_backstep_waacking_crunk", camera: "cam_distant_wide_master_to_hardcut_closeup", place: "plate_concrete_rooftop_parking_golden", wardrobe: "everyday_oversized_poplin_shirt_bike_shorts", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "house_jack_shuffle_126", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_solo_kpop_dancebreak_43", label: "💥 K-Pop Solo Dance Break (15s 4:3): 5-Cut Popping, Waacking & Hook-Kick Hang", values: { style: "style_kpop_music_bank_4k_stage", pose: "dance_solo_hyper_dancebreak_5cut_montage", camera: "cam_viral_dutch_90roll_wipe_cuts", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "action_cyber_idol_metallic_corset_boots", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_duet_gym_crunk_hook_hang_916", label: "🥁 Energy Duet: Mirror Gym Crunk Lock, Body Wave & Hook-Kick Hang (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", pose: "dance_duet_hook_kick_hang_quickstep_break", camera: "multi_angle_action_close", place: "plate_private_gym_mirror_weight_bench", wardrobe: "street_cargo_miniskirt_zip_hoodie_platforms", light: "soft_natural_light", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_crunk_waacking_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_simple_bedroom_nsfw_missionary_916", label: "🛏️ Simple Enclosed Bedroom: Casual Top Strip -> Bed Crawl -> Missionary (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", place: "plate_simple_enclosed_soft_natural_bedroom", light: "soft_natural_light", colour: "champagne_honey_glow", explicit: "cont_simple_bedroom_casual_strip_to_missionary", wardrobe: "street_oversized_boyfriend_hoodie_bare_legs", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_uber_stairwell_railing_brawl_169", label: "UBER FIGHT (ms): Cramped Concrete Stairwell Railing Toss & Slam (16:9)", values: { style: "john_wick_neon_gunfu", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_stairwell_railing_brawl", place: "plate_rainy_backstage_concert_tunnel", light: "cyber_dual_gel", colour: "crimson_john_wick_gold", wardrobe: "action_stealth_infiltration_turtleneck_harness", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_scifi_lab_onetake_brawl_169", label: "UBER FIGHT (ms): One-Take Sci-Fi Bio-Lab Table Vault, Spark Sweep & Penultimate Blast (16:9)", values: { style: "h3_astro_cinema", combat: "uber_fight_scifi_lab_table_vault_chamber_ko", camera: "cam_combat_kinetic_whip_zoom_ultimate", place: "plate_sterile_scifi_biolab_stainless_chamber", light: "cyber_dual_gel", colour: "teal_orange", fx: "vfx_kinetic_shockwave_dust_ring", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_jedi_sith_force_clash_169", label: "UBER FIGHT (ms): Jump Kicks, Mid-Air Force Clash & Penultimate Force Push Zoom (16:9)", values: { style: "h3_astro_cinema", combat: "uber_fight_jedi_sith_midair_force_clash", camera: "cam_combat_kinetic_whip_zoom_ultimate", place: "shattered_marble_lobby", light: "cyber_dual_gel", colour: "teal_orange", fx: "vfx_kinetic_shockwave_dust_ring", fx_timing: "from_start", music: "taiko_war_drums_138", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    // --- New K-Pop MV Choreography + Fingertips + Iconic Cuts (2026-11-18) ---
    { id: "__builtin_kpop_armageddon_finger_wave_916", label: "🦾 K-Pop MV: Finger-Wave Tutting + Gimbal Hand-Drop (9:16)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_inkigayo_ronin_hand_drop", pose: "dance_kpop_armageddon_finger_wave_tut", place: "plate_rainy_backstage_concert_tunnel", light: "cyber_dual_gel", colour: "colour_douyin_porcelain_neon_cyan", wardrobe: "action_cyber_idol_metallic_corset_boots", music: "kpop_whiplash_runway_electro_128", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_magnetic_finger_lock_916", label: "🧲 K-Pop MV 5th-Gen: Interlocked Finger-Tutting Loop + Cheek Curl (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", camera: "cam_kpop_anti_drop_macro_to_crane", pose: "dance_kpop_magnetic_finger_lock_916", place: "plate_mirror_dance_rehearsal_studio", light: "light_ring_beauty_plus_neon_rim", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", music: "kpop_siren_hyperpop_jersey_136", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_chkboom_crosshair_kick_169", label: "🎯 K-Pop MV: Crosshair Finger-Guns, Heel-Kick & Gimbal Drop (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_inkigayo_ronin_hand_drop", pose: "dance_kpop_chkboom_crosshair_kick", place: "plate_concrete_rooftop_parking_golden", light: "sunset_silhouette_halo_rim", colour: "teal_orange", wardrobe: "street_cropped_jacket_cargo", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_maestro_conductor_169", label: "🎼 K-Pop MV: Conductor Wrist-Flick, Anti-Drop Freeze & Crane Footwork (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_anti_drop_macro_to_crane", pose: "dance_kpop_maestro_conductor_footwork", place: "plate_marble_museum_rotunda_skylight", light: "light_kpop_concert_multi_spot_haze", colour: "kodak_vision3_500t", wardrobe: "street_idol_stage_coord_blazer_mini", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_girl_crush_bass_drop_124", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_duet_naughty_mirror_tutting_169", label: "🪞 K-Pop Duet MV: Arm-Window Peek, Mirror Tutting & Pillar Match-Truck (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_tutting_arm_window_frame,cam_kpop_through_wall_match_truck", dial_modes: { camera: "sequence" }, pose: "dance_kpop_duet_naughty_mirror_tutting", place: "plate_mirror_dance_rehearsal_studio", light: "editorial_softbox_beauty_key", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "tailored_black_blazer_trousers", music: "french_touch_filter_house_120", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_ddu_finger_gun_drop_916", label: "🔫 K-Pop MV: Dual Finger-Guns, Lens-Reach Drop & Crown Pose (9:16)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_inkigayo_ronin_hand_drop", pose: "dance_kpop_ddu_finger_gun_tilt_drop", place: "plate_proscenium_theater_stage_spotlight", light: "light_kpop_concert_multi_spot_haze", colour: "crimson_john_wick_gold", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_girl_crush_bass_drop_124", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_pinky_curl_chevron_916", label: "💅 K-Pop MV: Pinky-to-Thumb Blossom Curl & Diamond Frame (9:16)", values: { style: "korean_drama_glow", camera: "cam_beat_drop_punch_wide_combo", pose: "dance_kpop_pinky_curl_chevron_line", place: "plate_ballet_rehearsal_sunlit_atelier", light: "soft_natural_light", colour: "colour_kpop_pastel_milk_highlights", wardrobe: "street_balletcore_wrap_bolero_legwarmers", music: "city_pop_80s_112", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_kpop_supernova_lens_flick_169", label: "⚡ K-Pop MV: Lens-Flick Spark, Neck-Tick & Hyperpop Bounce (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_anti_drop_macro_to_crane", pose: "dance_kpop_supernova_lens_flick_bounce", place: "starship_observation_deck", light: "cyber_dual_gel", colour: "colour_douyin_porcelain_neon_cyan", wardrobe: "action_cyber_idol_metallic_corset_boots", music: "hyperpop_glitch_dance_145", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    // --- New Uber Fight Presets (2026-11-18) ---
    { id: "__builtin_uber_hk_neon_alley_wingchun_169", label: "⚔️🔥 UBER FIGHT (ms): Hong Kong Neon Rain Alley Elbow Flurry & Pipe Counter (16:9)", values: { style: "john_wick_neon_gunfu", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_hong_kong_neon_alley_wingchun_rain", place: "plate_rainy_chinatown_lantern_alley", light: "rain_neon_puddle_bounce", colour: "crimson_john_wick_gold", wardrobe: "street_cropped_jacket_cargo", fx: "fx_raindrop_on_camera_glass", fx_timing: "from_start", ambience: "neon_alley_puddle_footsteps", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_dragon_breath_topdown_169", label: "🔥🔫 UBER FIGHT (ms): Overhead Top-Down Twin-Drum Tracer SMG Corridor Clear (16:9)", values: { style: "john_wick_neon_gunfu", camera: "top_down_push", combat: "uber_fight_dragon_breath_topdown_corridor_gunfu", place: "abandoned_steel_foundry_sparks", light: "firelight", colour: "crimson_john_wick_gold", wardrobe: "action_stealth_infiltration_turtleneck_harness", fx: "vfx_muzzle_brass_storm", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_anime2real_taijutsu_crater_169", label: "🍥⚡ UBER FIGHT (ms): Anime2Real Taijutsu Blitz & Crater Sphere Slam (16:9)", values: { style: "anime2real_live_action_vfx", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_anime2real_shadow_clone_taijutsu_1v4", place: "plate_shibuya_rain_crosswalk_crater", light: "anime2real_elemental_aura_interactive_key", colour: "ufotable_neon_hdr_contrast", wardrobe: "anime2real_kunoichi_mesh_shinobi_suit", fx: "vfx_kinetic_shockwave_dust_ring", fx_timing: "from_start", music: "sakuga_anime_rock_165", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_skybridge_glass_parkour_169", label: "🏙️💥 UBER FIGHT (ms): Rooftop Glass Skybridge Parkour Chase & Skylight Smash (16:9)", values: { style: "h3_astro_cinema", camera: "track_side", combat: "uber_fight_parkour_rooftop_glass_skybridge_chase", place: "plate_concrete_rooftop_parking_golden", light: "golden_hour", colour: "teal_orange", wardrobe: "street_cropped_jacket_cargo", fx: "vfx_plate_glass_explosion", fx_timing: "from_start", music: "epic_hybrid_110", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_samurai_monsoon_bamboo_169", label: "⚔️🌧️ UBER FIGHT (ms): Monsoon Bamboo-Grove Triple Blade Deflection & Flash-Cut (16:9)", values: { style: "wuxia_wirefu_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_samurai_monsoon_bamboo_iaido_parry", place: "plate_snowy_bamboo_forest_moonlight", light: "lightning_storm_flash_rim", colour: "emerald_anime_midnight", wardrobe: "action_traditional_samurai_kimono_slit", fx: "vfx_sword_spark_shower", fx_timing: "from_start", ambience: "rain_heavy", music: "shamisen_taiko_battle_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_cyberpunk_bullet_deflect_169", label: "🤖⚡ UBER FIGHT (ms): Cyberpunk Highway Katana Bullet-Deflect Sprint & Cleave (16:9)", values: { style: "cyberpunk_edgerunners_neon", camera: "sandevistan_freeze_orbit_180", combat: "uber_fight_cyberpunk_katana_bullet_deflect_sprint", place: "tokyo_neon_rain_rooftop", light: "cyber_dual_gel", colour: "emerald_matrix_gunmetal", wardrobe: "street_cyberpunk_holo_jacket_straps", fx: "vfx_sword_spark_shower", fx_timing: "from_start", music: "cyberpunk_edgerunner_hyper_synth_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_kratos_frost_axe_169", label: "🪓❄️ UBER FIGHT (ms): Heavy Frost-Axe Throw, Shield Bash & Seismic Cleave (16:9)", values: { style: "h3_astro_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_kratos_frost_axe_shield_juggernaut_cleave", place: "burning_ancient_battlefield", light: "chiaroscuro_hard_slash", colour: "teal_orange", wardrobe: "action_battle_damaged_armor", fx: "vfx_crater_ground_crack", fx_timing: "from_start", music: "taiko_war_drums_138", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_vertical_stairwell_drop_916", label: "📱🔥 UBER FIGHT (ms): Vertical 9:16 Fire-Escape Shaft Drop & Neon Crash (9:16)", values: { style: "john_wick_neon_gunfu", camera: "staircase_vertigo_descent_track", combat: "uber_fight_vertical_stairwell_neon_drop_916", place: "plate_rainy_backstage_concert_tunnel", light: "cyber_dual_gel", colour: "crimson_john_wick_gold", wardrobe: "action_stealth_infiltration_turtleneck_harness", fx: "vfx_plate_glass_explosion", fx_timing: "from_start", music: "industrial_dark_metal_130", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    // --- Expanded Uber Fight, K-Pop MV Choreography, & Complete [Stage] Combos (2026-11-18) ---
    { id: "__builtin_uber_twin_p90_rave_club_169", label: "🎶🔥 UBER FIGHT (ms): Dual Suppressed PDWs Neon Rave Club Bar-Slide & Speed Reload (16:9)", values: { style: "john_wick_neon_gunfu", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_twin_p90_neon_rave_club_gunfu", place: "plate_rainy_backstage_concert_tunnel", wardrobe: "action_stealth_infiltration_turtleneck_harness", light: "club_laser_strobe_haze", colour: "crimson_john_wick_gold", fx: "vfx_muzzle_brass_storm", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_bullet_train_roof_monsoon_169", label: "🚄⛈️ UBER FIGHT (ms): Moving Bullet-Train Roof Monsoon Brawl & Gantry Duck (16:9)", values: { style: "h3_astro_cinema", camera: "whip_pan_reaction_match", combat: "uber_fight_bullet_train_roof_monsoon_brawl", place: "plate_highspeed_bullet_train_aisle", wardrobe: "street_cropped_jacket_cargo", light: "lightning_storm_flash_rim", colour: "teal_orange", fx: "fx_raindrop_on_camera_glass", fx_timing: "from_start", ambience: "rain_heavy", music: "industrial_dark_metal_130", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_anime2real_black_flash_169", label: "⚫⚡ UBER FIGHT (ms): Anime2Real Black-Flash Crimson Shockwave 1v3 Alley Blitz (16:9)", values: { style: "anime2real_live_action_vfx", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_anime2real_black_flash_alley_1v3", place: "plate_shibuya_rain_crosswalk_crater", wardrobe: "anime2real_jjk_sorcerer_high_collar", light: "anime2real_elemental_aura_interactive_key", colour: "ufotable_neon_hdr_contrast", fx: "vfx_anime2real_black_flash_crimson", fx_timing: "from_start", music: "sakuga_anime_rock_165", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_snow_bunker_dual_smg_169", label: "❄️🔫 UBER FIGHT (ms): Arctic Concrete Bunker Twin Compact SMG & Ice-Axe Breach (16:9)", values: { style: "h3_astro_cinema", camera: "track_side", combat: "uber_fight_snow_bunker_dual_vector_breach", place: "abandoned_steel_foundry_sparks", wardrobe: "action_stealth_infiltration_turtleneck_harness", light: "chiaroscuro_hard_slash", colour: "cool_steel", fx: "vfx_muzzle_brass_storm", fx_timing: "from_start", music: "epic_hybrid_110", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_kendo_dojo_iaido_169", label: "⚔️⚡ UBER FIGHT (ms): Storm Dojo Twin-Katana Disarm & Lightning Iaido Cross-Slash (16:9)", values: { style: "wuxia_wirefu_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_kendo_dojo_twin_katana_iaido", place: "traditional_martial_dojo", wardrobe: "action_traditional_samurai_kimono_slit", light: "lightning_storm_flash_rim", colour: "emerald_anime_midnight", fx: "vfx_sword_spark_shower", fx_timing: "from_start", ambience: "dojo_wood_creak_wind", music: "shamisen_taiko_battle_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_neon_arcade_chain_916", label: "🕹️⛓️ UBER FIGHT (ms): Vertical 9:16 Neon Arcade Cabinet Vault & Chain-Hook Knee (9:16)", values: { style: "john_wick_neon_gunfu", camera: "staircase_vertigo_descent_track", combat: "uber_fight_neon_arcade_chain_hook_parkour", place: "plate_abandoned_neon_arcade_cabinets", wardrobe: "street_cyberpunk_holo_jacket_straps", light: "cyber_dual_gel", colour: "colour_douyin_porcelain_neon_cyan", fx: "vfx_plate_glass_explosion", fx_timing: "from_start", ambience: "neon_arcade_parlor", music: "cyberpunk_edgerunner_hyper_synth_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_penthouse_bar_judo_169", label: "🥃🥋 UBER FIGHT (ms): Skyline Penthouse Marble-Bar Knee Slide & Judo Glass Slam (16:9)", values: { style: "john_wick_neon_gunfu", camera: "whip_pan_reaction_match", combat: "uber_fight_penthouse_bar_tuxedo_judo_cqc", place: "shattered_marble_lobby", wardrobe: "tailored_black_blazer_trousers", light: "chiaroscuro_hard_slash", colour: "crimson_john_wick_gold", fx: "vfx_glass_shard_slowmo_glitter", fx_timing: "from_start", music: "john_wick_club_techno_132", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_uber_wuxia_dragon_spear_169", label: "🏮🎋 UBER FIGHT (ms): Wuxia Blossom Courtyard Dragon-Spear & Pillar Rebound (16:9)", values: { style: "wuxia_wirefu_cinema", camera: "cam_combat_kinetic_whip_zoom_ultimate", combat: "uber_fight_wuxia_courtyard_dragon_spear", place: "plate_anime2real_soul_society_cherry_blossom_courtyard", wardrobe: "action_traditional_samurai_kimono_slit", light: "moonlight", colour: "emerald_anime_midnight", fx: "vfx_anime2real_sakura_petal_bladestorm", fx_timing: "from_start", music: "taiko_war_drums_138", motion: "max", energy: "peak", expression: "stoic", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_crown_tilt_walk_916", label: "👑 K-Pop Solo MV: Studio-Choom Crimson Strobe Dolly & Crown-Tilt Walk (9:16)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_studio_choom_crimson_dolly_snap", pose: "dance_kpop_crown_tilt_claw_walk_916", place: "minimal_cyclorama_set", wardrobe: "street_kpop_velvet_crop_asymmetric_mini", light: "light_kpop_concert_multi_spot_haze", colour: "crimson_john_wick_gold", music: "kpop_girl_crush_bass_drop_124", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_duet_diamond_switch_169", label: "💎 K-Pop Duet MV: Back-to-Back Switch, Shoulder-Tap Pop & Halo Drop (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_choreo_overhead_halo_drop", pose: "dance_kpop_duet_diamond_switch_cannon_169", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "street_idol_stage_coord_blazer_mini", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_lasso_chest_pop_916", label: "🤠 K-Pop 4th-Gen: Overhead Lasso Spin, Double Chest-Pop & Lens Grab (9:16)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_inkigayo_ronin_hand_drop", pose: "dance_kpop_hip_isolation_lasso_snap_916", place: "plate_concrete_rooftop_parking_golden", wardrobe: "street_cropped_jacket_cargo", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", music: "kpop_whiplash_runway_electro_128", motion: "max", energy: "peak", expression: "vivid", expr_read: "sly", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_y2k_breeze_peace_916", label: "✌️ K-Pop Y2K Fresh Breeze: Hop-Skip, Wind Hair-Flip & Double V-Sign (9:16)", values: { style: "style_y2k_digicam_direct_flash", camera: "cam_beat_snap_micro_push", pose: "dance_kpop_y2k_breeze_hairflip_peace_916", place: "plate_ballet_rehearsal_sunlit_atelier", wardrobe: "street_coquette_ribbon_cardigan_pleated_mini", light: "soft_natural_light", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_y2k_ukgarage_bounce_122", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_duet_siren_cross_169", label: "🧜‍♀️ K-Pop Duet MV: Siren Cross-Step, Temple Slice & Waist-Dip Hold (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_kpop_through_wall_match_truck", pose: "dance_kpop_duet_siren_backstep_cross_169", place: "plate_mirror_dance_rehearsal_studio", wardrobe: "glam_backless_crystal_chain_cowl_dress", light: "editorial_softbox_beauty_key", colour: "colour_kpop_pastel_milk_highlights", music: "kpop_sensual_velvet_rnb_98", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_kpop_cyber_visor_moonwalk_916", label: "🤖 K-Pop Cyber MV: Visor-Swipe, Knuckle-Box Tutting & Moonwalk Freeze (9:16)", values: { style: "style_douyin_highgloss_neon_beauty", camera: "cam_kpop_studio_choom_crimson_dolly_snap", pose: "dance_kpop_cyber_gloves_visor_scan_916", place: "plate_neon_cyber_ramen_shop_rain", wardrobe: "action_cyber_idol_metallic_corset_boots", light: "cyber_dual_gel", colour: "colour_douyin_porcelain_neon_cyan", music: "kpop_siren_hyperpop_jersey_136", motion: "max", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_kpop_chair_velvet_legcross_916", label: "🪑 K-Pop Velvet Chair Stage: Heel-Hook Spin, Jacket-Slip & Backrest Pose (9:16)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_contour_shoulder_hip_glide", pose: "dance_kpop_chair_velvet_legcross_snap_916", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "street_idol_stage_coord_blazer_mini", light: "tokyo_love_hotel_magenta_violet_velvet", colour: "velvet_crimson_gold", music: "kpop_sensual_velvet_rnb_98", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "silent" } },
    { id: "__builtin_kpop_duet_finale_confetti_169", label: "🎊 K-Pop Encore Duet: Linked-Arm Spin, Knee-Bounce & Twin Ending Fairy (16:9)", values: { style: "style_kpop_music_bank_4k_stage", camera: "cam_360_slowmo_duet_orbit", pose: "dance_kpop_duet_finale_confettispin_169", place: "plate_proscenium_theater_stage_spotlight", wardrobe: "street_balletcore_wrap_bolero_legwarmers", light: "light_kpop_concert_multi_spot_haze", colour: "colour_kpop_pastel_milk_highlights", fx: "fx_kpop_confetti_sparkle_cannon", fx_timing: "from_start", music: "kpop_hyper_hype_train_134", motion: "max", energy: "peak", expression: "vivid", expr_read: "warm", life: "hyper", talk_mode: "silent" } },
    { id: "__builtin_stage_gym_mat_split_916", label: "NSFW 2-Stage: Studio Mirror Stretch -> Padded Gym Mat Rear Entry (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "stage_gym_mat_split_stretch_to_rear", place: "plate_private_gym_mirror_weight_bench", wardrobe: "partial_yoga_leggings_peeled_mid_thigh", light: "soft_natural_light", colour: "champagne_honey_glow", ambience: "gym_locker_bench_echo", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_kitchen_island_169", label: "NSFW 2-Stage: Marble Kitchen Island Edge Tease -> Hip-High Press (16:9)", values: { style: "glamour_boudoir_8k", camera: "coverage_match_on_action", explicit: "stage_kitchen_island_seat_to_press", place: "plate_luxury_kitchen_island_night", wardrobe: "partial_blouse_open_bra_pushed_up", light: "penthouse_blue_amber", colour: "champagne_honey_glow", ambience: "penthouse_night_hum", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_aftercare_whisper_169", label: "NSFW Aftercare Stage: Fireplace Silk Breathing & Skin Rest (16:9)", values: { style: "h3_astro_cinema", camera: "static_close", explicit: "stage_aftercare_cooldown_whisper", place: "plate_satin_four_poster_fireplace_cabin", wardrobe: "partial_silk_robe_open_front", fetish: "aftercare_cuddle_pillow_talk", light: "fireplace_ember_warm_low", colour: "champagne_honey_glow", talkstyle: "husky_aftercare_murmur", ambience: "fireplace_ember_pop_silk", motion: "slow", energy: "hush", expression: "subtle", expr_read: "warm", life: "natural", talk_mode: "auto" } },
    { id: "__builtin_stage_balcony_skyline_916", label: "NSFW 2-Stage: Night Skyline Balcony Rail Arch -> Lifted Carry Thrusts (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "portrait_vertical_stack", explicit: "stage_balcony_skyline_2cut_rail_to_carry", place: "luxury_hotel_balcony_night", wardrobe: "partial_dress_hiked_waist", light: "moonlight", colour: "champagne_honey_glow", ambience: "city_night", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_hotel_window_bed_169", label: "NSFW 3-Stage: Sheer-Curtain Suite Silhouette -> Oral -> Bed Missionary (16:9)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", explicit: "stage_hotel_window_silhouette_to_bed", place: "plate_sunlit_french_balcony_sheers", wardrobe: "lingerie_pearl_mesh_teddy_sheer_robe", light: "dappled_sunlight_sheer_curtains", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_spa_hammam_169", label: "NSFW 3-Stage: Marble Hammam Steam Bench -> Wet Oral -> Deep Rear Entry (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_spa_hammam_3cut_steam_bench", place: "plate_marble_hammam_steam_bathhouse", wardrobe: "nude_wet_shower", light: "soft_natural_window", colour: "champagne_honey_glow", ambience: "bathhouse_steam_water_drip", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_lesbian_vanity_916", label: "NSFW 2-Stage: Lesbian Vanity Mirror Breast Kiss -> Seated Tribadism (9:16)", values: { style: "glamour_boudoir_8k", camera: "mirror_three_way_reflection", explicit: "stage_lesbian_vanity_mirror_double_tease", place: "glamour_vanity_ringlight", wardrobe: "nude_both_partners", light: "bathroom_vanity_mirror_bulbs", colour: "peach_milk_gravure", ambience: "intimate_skin_foley", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_slow_grind_insertion_916", label: "NSFW 3-Stage Slow-Burn: Eye-Contact Lap Grind -> Tip Tease -> Deep Sink (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "stage_slow_grind_lap_tease_insertion", place: "penthouse_silk_bedroom", wardrobe: "partial_sweater_dress_hiked_over_hips", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", motion: "slow", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_mmf_alternating_169", label: "NSFW 3-Stage MMF: Alternating Oral + Fingering -> Spitroast -> Double Finish (16:9)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", explicit: "stage_mmf_alternating_focus_3cut", place: "plate_penthouse_master_bed_mirror", wardrobe: "nude_all_cast_subjects_s1_s9", light: "red_velvet_boudoir", colour: "crimson_john_wick_gold", ambience: "intimate_skin_foley", motion: "brisk", energy: "peak", expression: "vivid", expr_read: "sensual", life: "hyper", talk_mode: "auto" } },
    { id: "__builtin_stage_balcony_sunset_press_916", label: "NSFW 2-Stage: Golden-Hour Balcony Kneeling Oral -> Glass-Door Press (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "stage_balcony_sunset_oral_to_window_press", place: "plate_sunlit_french_balcony_sheers", wardrobe: "partial_dress_hiked_waist", light: "sunset_silhouette_halo_rim", colour: "colour_golden_hour_bronze_glow", ambience: "intimate_skin_foley", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_office_late_night_916", label: "NSFW 3-Stage Office: Desk-Edge Kiss -> Swivel Chair Oral -> Glass Doggy (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "portrait_vertical_stack", explicit: "stage_office_3cut_desk_kiss_chair_glass", place: "executive_corner_office_midnight", wardrobe: "partial_office_pencil_skirt_unzipped_dropped", light: "penthouse_blue_amber", colour: "champagne_honey_glow", talkstyle: "secretive_office_whisper", ambience: "penthouse_night_hum", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_wall_to_bed_contrast_169", label: "NSFW 2-Stage Contrast: Intense Standing Wall-Pin -> Tender Bed Missionary (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_rough_to_tender_wall_to_bed", place: "plate_penthouse_master_bed_mirror", wardrobe: "nude_full", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", ambience: "intimate_skin_foley", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_ffm_threesome_169", label: "NSFW 3-Stage FFM: Dual Oral Tease -> Alternating Cowgirl & Face-Sit (16:9)", values: { style: "glamour_boudoir_8k", camera: "multi_position_3cut_intimate", explicit: "stage_ffm_3cut_dual_oral_alternating_ride", place: "plate_penthouse_master_bed_mirror", wardrobe: "nude_all_cast_subjects_s1_s9", light: "candlelight_flicker_boudoir", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_wine_cellar_169", label: "NSFW 2-Stage: Oak Wine-Cellar Tasting-Table Lift -> Candlelit Missionary (16:9)", values: { style: "erotic_thriller_90s_35mm", camera: "coverage_match_on_action", explicit: "stage_wine_cellar_2cut_table_lift_to_missionary", place: "plate_private_wine_cellar_candlelight", wardrobe: "partial_evening_gown_bodice_peeled_waist", light: "candlelight_flicker_boudoir", colour: "velvet_crimson_gold", ambience: "intimate_skin_foley", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_desk_siren_916", label: "NSFW 3-Stage Office Siren: Blouse & Glasses Tease -> Under-Desk -> Cowgirl (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "portrait_vertical_stack", explicit: "stage_desk_siren_3cut_glasses_tease_cowgirl", place: "executive_corner_office_night", wardrobe: "fetish_office_siren_skirt", light: "blinds", colour: "champagne_honey_glow", talkstyle: "cocky_dominant_commentary", ambience: "penthouse_night_hum", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_lesbian_poolside_169", label: "NSFW 2-Stage Lesbian: Wet Waterline Kiss -> Sunbed Mutual Thigh Ride (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_lesbian_poolside_wet_kiss_to_sunbed", place: "plate_rooftop_infinity_pool_skyline", wardrobe: "partial_bikini_top_untied_sliding", light: "sunset_silhouette_halo_rim", colour: "honey_bronze_sun_glow", ambience: "yacht_waves_teak_breeze", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_mmf_standing_169", label: "NSFW 3-Stage MMF Standing: DP Sandwich -> Double Oral -> Twin Finish (16:9)", values: { style: "erotic_thriller_90s_35mm", camera: "multi_angle_orbit_arc_cut", explicit: "stage_mmf_standing_split_focus_3cut", place: "plate_tokyo_love_hotel_mirror_ceiling_suite", wardrobe: "nude_all_cast_subjects_s1_s9", light: "tokyo_love_hotel_magenta_violet_velvet", colour: "magenta_violet_bisexual_lighting", ambience: "intimate_skin_foley", motion: "brisk", energy: "peak", expression: "vivid", expr_read: "intense", life: "hyper", talk_mode: "auto" } },
    { id: "__builtin_stage_simple_bedroom_3cut_916", label: "NSFW 3-Stage Simple Bedroom: Distant Undress -> Bed Oral -> Cowgirl (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "stage_simple_bedroom_3cut_oral_cowgirl_doggy", place: "plate_simple_enclosed_soft_natural_bedroom", wardrobe: "street_oversized_boyfriend_hoodie_bare_legs", light: "soft_natural_light", colour: "champagne_honey_glow", ambience: "silk_sheets_skin_breath", motion: "natural", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_onsen_cedar_3cut_169", label: "NSFW 3-Stage Onsen: Steaming Cedar Embrace -> Wet Rim Oral -> Rear Entry (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_onsen_cedar_3cut_soak_lap_rear", place: "japanese_onsen_cedar_steam", wardrobe: "nude_full", light: "candlelit_obsidian_bath_gold_ripples", colour: "champagne_honey_glow", ambience: "bathhouse_steam_water_drip", motion: "slow", energy: "steady", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_dungeon_velvet_3cut_916", label: "NSFW 3-Stage Femdom: Collar Leash -> Latex Crop Tease -> Domme Cowgirl (9:16)", values: { style: "erotic_thriller_90s_35mm", camera: "low_angle_power_pedestal", explicit: "stage_dungeon_velvet_3cut_collar_spank_ride", place: "bdsm_red_dungeon_cross", wardrobe: "fetish_latex_catsuit_unzipped", fetish: "collar_leash_petplay_walk", light: "red_velvet_boudoir", colour: "crimson_john_wick_gold", talkstyle: "commanding_mommy_domme", ambience: "leather_leash_chain_clink_heels", motion: "brisk", energy: "charged", expression: "vivid", expr_read: "sly", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_private_jet_3cut_169", label: "NSFW 3-Stage Private Jet: Club-Chair Kiss -> Mile-High Oral -> Aft Suite (16:9)", values: { style: "glamour_boudoir_8k", camera: "orbit_push", explicit: "stage_private_jet_3cut_champagne_oral_bed", place: "plate_private_jet_leather_cabin", wardrobe: "partial_evening_gown_bodice_peeled_waist", light: "sunset_silhouette_halo_rim", colour: "champagne_honey_glow", ambience: "private_jet_cabin_hum", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
    { id: "__builtin_stage_rooftop_hot_tub_3cut_916", label: "NSFW 3-Stage Rooftop Hot Tub: Rainy Bubble Rub -> Rim Oral -> Water Ride (9:16)", values: { style: "glamour_boudoir_8k", camera: "portrait_vertical_stack", explicit: "stage_neon_rain_penthouse_tub_3cut", place: "plate_rainy_penthouse_hot_tub_terrace", wardrobe: "nude_full", light: "neon_rain_window_caustics", colour: "champagne_honey_glow", ambience: "jacuzzi_bubbles_candle_crackle", motion: "natural", energy: "charged", expression: "vivid", expr_read: "sensual", life: "alive", talk_mode: "auto" } },
];

const ALL_DIAL_KEYS = [
    "camera", "light", "style", "place", "wardrobe", "combat", "explicit", "talkstyle",
    "lens", "colour", "fx", "pose", "fetish", "character", "tv_show", "era", "accent", "ambience", "music",
];

const PRIMARY_DIALS = [
    ["camera", "Cam · Auto"],
    ["light", "Light · Auto"],
    ["style", "Style · Auto"],
    ["place", "Place · Auto"],
    ["wardrobe", "Wear · Auto"],
    ["combat", "Action · Off"],
    ["explicit", "Stage · Off"],
    ["talkstyle", "Speech · Auto"],
];

const SECONDARY_DIALS = [
    ["lens", "Optics · Auto"],
    ["colour", "Grade · Auto"],
    ["fx", "FX · None"],
    ["pose", "Dance / Pose · Auto"],
    ["fetish", "Playbook · Off"],
    ["character", "Cast Type · Rail"],
    ["tv_show", "Genre · Auto"],
    ["era", "Era · Present"],
    ["accent", "Accent · Default"],
    ["ambience", "Ambience · Auto"],
    ["music", "Music · Auto"],
];

export function readRigState(node) {
    let st = {};
    try {
        const rw = widgetByName(node, "rig_state");
        if (rw?.value) st = JSON.parse(String(rw.value) || "{}") || {};
    } catch {}
    if (!st || typeof st !== "object") st = {};
    let fl = (st.flavors && typeof st.flavors === "object") ? st.flavors : null;
    if (!fl) {
        try {
            fl = JSON.parse(String(widgetByName(node, "flavors_json")?.value || "{}") || "{}");
        } catch {
            fl = {};
        }
    }
    return {
        prompt_out: String(st.prompt_out ?? widgetByName(node, "prompt_out")?.value ?? ""),
        storyboard_out: String(st.storyboard_out ?? widgetByName(node, "storyboard_out")?.value ?? ""),
        ref_plan_json: String(st.ref_plan_json ?? widgetByName(node, "ref_plan_json")?.value ?? ""),
        flavors: (fl && typeof fl === "object") ? fl : {},
    };
}

export function patchRigState(node, patch) {
    const cur = readRigState(node);
    const next = Object.assign({}, cur, patch || {});
    const rw = widgetByName(node, "rig_state");
    if (rw) {
        rw.value = JSON.stringify(next);
        try { rw.callback?.(rw.value, node.graph?.canvas, node); } catch (_) {}
    }
    const legacy = [
        ["prompt_out", next.prompt_out],
        ["storyboard_out", next.storyboard_out],
        ["ref_plan_json", next.ref_plan_json],
        ["flavors_json", JSON.stringify(next.flavors || {})],
    ];
    for (const [wn, val] of legacy) {
        const w = widgetByName(node, wn);
        if (w) {
            w.value = val;
            try { w.callback?.(val, node.graph?.canvas, node); } catch (_) {}
        }
    }
    return next;
}

export function h3FormatCodeFromLabel(fmtVal) {
    const s = String(fmtVal || "");
    if (s.includes("I2VA")) return "h3_i2va";
    if (s.includes("FL2VA")) return "h3_fl2va";
    if (s.includes("L2VA")) return "h3_l2va";
    if (s.includes("Start Frame")) return "h3_keyframe";
    if (s.includes("Beats")) return "h3_beats";
    return "h3_auto";
}

let _sharedCatalog = null;
let _sharedStatus = { running: false, backend: "ninfer", backend_label: "nInfer", model: "" };

function parseMultiValue(raw) {
    if (!raw) return [];
    const arr = Array.isArray(raw) ? raw : String(raw).split(",");
    const out = [];
    const seen = new Set();
    for (const part of arr) {
        const s = String(part || "").trim();
        if (!s || s === "none" || seen.has(s)) continue;
        seen.add(s);
        out.push(s);
    }
    return out;
}

function serializeMultiValue(arr) {
    return (arr || []).filter(Boolean).join(",");
}

function parseAspectSpec(raw) {
    const s = String(raw || "").trim();
    const m = s.match(/(\d+)\s*:\s*(\d+)/);
    if (m) {
        const w = Number(m[1]);
        const h = Number(m[2]);
        const label = `${w}:${h}`;
        if (w > 0 && h > 0) {
            if (h > w) return { label, bucket: "9:16" };
            if (w > h) return { label, bucket: "16:9" };
            return { label, bucket: "either" };
        }
    }
    if (/portrait|vertical/i.test(s)) return { label: "9:16", bucket: "9:16" };
    return { label: "16:9", bucket: "16:9" };
}

function createSandTieCore(node, {
    mountBody,
    briefEl,
    planBox,
    blockBox,
    say,
    saveDraft,
    getDurationLabel,
    getAspect,
    getRefPlan,
    setRefPlan,
    getStartImage,
    getVoiceFiles,
    previousHopContext,
    setBusyState,
    isBusy,
    standalone = false,
    onApplyStandalone = null,
    onDialsChanged = null,
    legacyButtons = null,
}) {
    ensureMselStyle();

    const defaultFlavors = {
        time_tied: true, kinetic_grip: true, eye_scan: true, double_knot: true, wake_writer: true,
        link_prev_hop: false,
        fx_timing: "delayed_mid", talk_mode: "auto", sound_mode: "auto",
        motion: "natural", life: "natural", energy: "steady", expression: "natural", expr_read: "auto",
        pov: "off", steering_bind: false, steering_scope: "blocks_0_24 (voice safe)",
        camera: "", light: "", lens: "", fx: "", style: "", colour: "", place: "", wardrobe: "",
        combat: "", explicit: "", fetish: "", pose: "", character: "", tv_show: "", era: "",
        talkstyle: "", accent: "", ambience: "", music: "", dial_modes: {},
    };

    const PERF_LEVEL_SPEC = {
        motion: [
            ["freeze", "Freeze", -2.0, "Near-still anchored stance"],
            ["slow", "Slow", -1.0, "Unhurried deliberate travel"],
            ["natural", "Nat", 0.0, "Lifelike physical speed"],
            ["brisk", "Brisk", 1.0, "Crisp athletic snap"],
            ["max", "Max", 2.0, "High-velocity burst motion"],
        ],
        energy: [
            ["hush", "Hush", -2.0, "Whisper-quiet tense poise"],
            ["calm", "Calm", -1.0, "Relaxed conversational tone"],
            ["steady", "Steady", 0.0, "Balanced dramatic drive"],
            ["charged", "Charged", 1.0, "Spirited urgent projection"],
            ["peak", "Peak", 2.0, "Peak dramatic intensity"],
        ],
        expression: [
            ["stoic", "Stoic", -2.0, "Minimal deadpan restraint"],
            ["subtle", "Subtle", -1.0, "Quiet eye/brow micro-reads"],
            ["natural", "Nat", 0.0, "Clear readable facial turns"],
            ["vivid", "Vivid", 1.0, "Expressive charismatic acting"],
            ["theatrical", "Theat", 2.0, "Bold theatrical expression"],
        ],
        life: [
            ["lock", "Lock", -2.0, "Quiet blinks & breath only"],
            ["subtle", "Subtle", -1.0, "Calm room air & breath"],
            ["natural", "Nat", 0.0, "Natural breath & ambient drift"],
            ["alive", "Alive", 1.0, "Active hair/cloth & prop life"],
            ["hyper", "Hyper", 2.0, "Full layered kinetic environment"],
        ],
    };

    function normPerfVal(axis, val) {
        const s = String(val ?? "").trim().toLowerCase();
        const aliasMap = {
            motion: { small: "slow", medium: "natural", large: "max", still: "freeze", nat: "natural", fast: "brisk", explosive: "max" },
            energy: { small: "calm", medium: "steady", large: "peak", hushed: "hush", natural: "steady", high: "charged" },
            expression: { small: "subtle", medium: "natural", large: "theatrical", deadpan: "stoic", nat: "natural", theat: "theatrical" },
            life: { small: "subtle", medium: "natural", large: "hyper", locked: "lock", nat: "natural" },
        };
        const mapped = aliasMap[axis]?.[s] || s;
        const rows = PERF_LEVEL_SPEC[axis] || [];
        if (rows.some((r) => r[0] === mapped)) return mapped;
        return rows[2]?.[0] || "natural";
    }

    function normalizePerfFlavors(obj) {
        if (!obj || typeof obj !== "object") return;
        for (const ax of ["motion", "energy", "expression", "life"]) {
            obj[ax] = normPerfVal(ax, obj[ax]);
        }
        if (!obj.expr_read) obj.expr_read = "auto";
        if (!obj.sound_mode) obj.sound_mode = "auto";
        if (!obj.steering_scope) obj.steering_scope = "blocks_0_24 (voice safe)";
    }

    function loadFlavors() {
        try {
            const raw = standalone
                ? (readRigState(node).flavors || {})
                : (node.properties?.[FLAVOR_PROP] || {});
            const merged = Object.assign({}, defaultFlavors, raw && typeof raw === "object" ? raw : {});
            // Map legacy switch names if present
            if ("fast_engine" in raw && !("time_tied" in raw)) merged.time_tied = Boolean(raw.fast_engine);
            if ("verbmaxxx" in raw && !("kinetic_grip" in raw)) merged.kinetic_grip = Boolean(raw.verbmaxxx);
            if ("vision_scan" in raw && !("eye_scan" in raw)) merged.eye_scan = Boolean(raw.vision_scan);
            if ("pass2_refine" in raw && !("double_knot" in raw)) merged.double_knot = Boolean(raw.pass2_refine);
            if ("auto_wake" in raw && !("wake_writer" in raw)) merged.wake_writer = Boolean(raw.auto_wake);
            if (!("motion" in raw) && "energy" in raw) merged.motion = normPerfVal("motion", raw.energy);
            normalizePerfFlavors(merged);
            merged.dial_modes = Object.assign({}, raw?.dial_modes || {});
            return merged;
        } catch {
            return Object.assign({}, defaultFlavors, { dial_modes: {} });
        }
    }

    const flavors = loadFlavors();

    function persistFlavors() {
        if (standalone) {
            patchRigState(node, { flavors: Object.assign({}, flavors, { dial_modes: Object.assign({}, flavors.dial_modes || {}) }) });
        } else {
            node.properties ??= {};
            node.properties[FLAVOR_PROP] = Object.assign({}, flavors, { dial_modes: Object.assign({}, flavors.dial_modes || {}) });
        }
        try { onDialsChanged?.(); } catch (_) {}
    }

    const undoStack = [];
    function pushUndoSnapshot() {
        const snap = { brief: briefEl.value, plan: planBox.value, block: blockBox.value, flavors: JSON.stringify(flavors) };
        const top = undoStack[undoStack.length - 1];
        if (top && top.brief === snap.brief && top.plan === snap.plan && top.block === snap.block && top.flavors === snap.flavors) return;
        undoStack.push(snap);
        if (undoStack.length > 15) undoStack.shift();
        syncUndoBtn();
    }

    const shell = el("div", "h3st-shell");

    // 1. Header bar (Brand + Combos + Smart Actions)
    const headRow = el("div", "h3st-head");
    const brandLeft = el("div", "h3st-row");
    const brandTitle = el("strong", null, "⌖ SandTie Scribe");
    brandTitle.style.color = "var(--h3-text)";
    const activeCountPill = el("span", "h3st-pill", "0 active");
    brandLeft.append(brandTitle, activeCountPill);

    const comboSel = el("select", "h3e-select");
    comboSel.style.maxWidth = "190px";
    comboSel.title = "Load a built-in or saved SandTie preset combo";
    const saveComboBtn = button("+ Save", "Save active dials as a custom combo", saveUserCombo);
    const delComboBtn = button("×", "Delete selected saved combo", deleteUserCombo);
    const surpriseBtn = button("Surprise Roll", "Domain-locked & aspect-safe creative roll (excludes multi-hop-only join rigs)", runSurpriseRoll);
    const matchBtn = button("Match Dials", "Analyze brief text & wired refs to pick fitting dials automatically", runMatchDials);
    const briefBtn = button("Compose Brief", "Draft a clean descriptive brief from wired Reference Bible & active dials", runComposeBrief);
    const resetBtn = button("Reset", "Reset all 19 dials (keeps switches & brief)", resetAllDials);

    const headRight = el("div", "h3st-row");
    headRight.append(comboSel, saveComboBtn, delComboBtn, surpriseBtn, matchBtn, briefBtn, resetBtn);
    headRow.append(brandLeft, headRight);

    // 2. Switches + Writer Status bar
    const swRow = el("div", "h3st-sw-bar");
    function makeSw(key, icon, text, tip) {
        const lbl = el("label", "h3st-sw");
        lbl.title = tip;
        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.checked = Boolean(flavors[key]);
        chk.addEventListener("change", () => {
            flavors[key] = chk.checked;
            persistFlavors();
        });
        lbl.append(chk, el("span", null, `${icon} ${text}`));
        return { lbl, chk };
    }
    const swTime = makeSw("time_tied", "⏱", "Time-Tied", "Send Shot-Tree & StateLedger blueprint (<shot_blueprint>) to lock cuts, carried attire, and weighted micro-beats");
    const swKinetic = makeSw("kinetic_grip", "⚡", "Kinetic Flow", "Natural weight transfer, grounded hands & smooth beat transitions (yields at calm Motion)");
    const swEye = makeSw("eye_scan", "👁", "Eye Scan", "2.5 MP cached reference scan locking likeness & attire without overriding hop pose");
    const swDouble = makeSw("double_knot", "✧", "Double-Knot", "Pass-2 continuity audit verifying Shot-Tree cuts, carried outfit/orientation, domains, positive English & zero semicolons");
    const swWake = makeSw("wake_writer", "☕", "Auto-Wake", "Auto-start nInfer if VRAM was evicted by a render");
    swWake.lbl.style.fontSize = "11px";

    const writerModeSel = el("select", "h3e-select");
    writerModeSel.style.marginLeft = "auto";
    writerModeSel.style.maxWidth = "116px";
    writerModeSel.title = "Writer connection: Local server (any OpenAI-compatible: LM Studio, llama-server, Ollama, KoboldCpp, vLLM) or nInfer";
    for (const [bid, blbl] of [["lmstudio", "Local server"], ["ninfer", "nInfer"]]) {
        const o = el("option", null, blbl);
        o.value = bid;
        writerModeSel.appendChild(o);
    }
    writerModeSel.addEventListener("change", async () => {
        const nextBack = writerModeSel.value;
        const lbl = nextBack === "ninfer" ? "nInfer" : "Local server";
        cfgBackSel.value = nextBack;
        cfgPathRow.hidden = nextBack !== "ninfer";
        statusPill.textContent = `Checking ${lbl}…`;
        statusPill.className = "h3st-pill";
        try {
            await fetch(LLM_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ backend: nextBack }),
            });
            await Promise.all([
                refreshStatus(false),
                writerCfgDrawer.hidden ? Promise.resolve() : loadWriterSettings(),
            ]);
        } catch (_) {}
    });

    const statusPill = el("span", "h3st-pill", "Checking writer…");
    const startBtn = button("Start", "Launch local nInfer writer server", () => toggleServer("start"));
    const stopBtn = button("Stop", "Stop local writer to free VRAM", () => toggleServer("stop"));
    const cfgBtn = button("⚙", "Configure Writer URL, Model & Server Exe", () => {
        const open = writerCfgDrawer.hidden;
        writerCfgDrawer.hidden = !open;
        cfgBtn.classList.toggle("h3st-chip-on", open);
        if (open) loadWriterSettings();
    });
    swRow.append(swTime.lbl, swKinetic.lbl, swEye.lbl, swDouble.lbl, writerModeSel, statusPill, startBtn, stopBtn, swWake.lbl, cfgBtn);

    const writerCfgDrawer = el("div", "h3st-drawer");
    writerCfgDrawer.hidden = true;
    const cfgBackSel = el("select", "h3e-select");
    cfgBackSel.style.maxWidth = "125px";
    cfgBackSel.addEventListener("change", async () => {
        const nextBack = cfgBackSel.value;
        const lbl = nextBack === "ninfer" ? "nInfer" : "Local server";
        writerModeSel.value = nextBack;
        cfgPathRow.hidden = nextBack !== "ninfer";
        statusPill.textContent = `Checking ${lbl}…`;
        statusPill.className = "h3st-pill";
        try {
            await fetch(LLM_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ backend: nextBack }),
            });
            await Promise.all([loadWriterSettings(), refreshStatus(false)]);
        } catch (_) {}
    });
    const cfgUrlInp = el("input", "h3e-writer-brief");
    cfgUrlInp.type = "text";
    cfgUrlInp.placeholder = "http://127.0.0.1:1234";
    cfgUrlInp.style.flex = "1 1 170px";
    const cfgModelInp = el("input", "h3e-writer-brief");
    cfgModelInp.type = "text";
    cfgModelInp.placeholder = "model id (optional / auto after Start)";
    cfgModelInp.title = "API model ID reported over /v1/models (not a file path; leave blank to auto-pick once running).";
    cfgModelInp.style.flex = "1 1 170px";
    const cfgModelPick = el("select", "h3e-select");
    cfgModelPick.style.maxWidth = "175px";
    cfgModelPick.addEventListener("change", () => {
        if (cfgModelPick.value) cfgModelInp.value = cfgModelPick.value;
    });
    const cfgUnloadLbl = el("label", "h3st-sw");
    const cfgUnloadChk = document.createElement("input");
    cfgUnloadChk.type = "checkbox";
    cfgUnloadChk.checked = true;
    cfgUnloadLbl.append(cfgUnloadChk, el("span", null, "Unload on Run"));
    const cfgSaveBtn = button("Save & Test", "Save writer connection and refresh model list", () => saveWriterSettings(), "h3e-btn h3e-btn-accent");
    const cfgRow = el("div", "h3st-row");
    cfgRow.append(el("strong", null, "Writer:"), cfgBackSel, cfgUrlInp, cfgModelInp, cfgModelPick, cfgUnloadLbl, cfgSaveBtn);

    const cfgPathRow = el("div", "h3st-row");
    const cfgExeInp = el("input", "h3e-writer-brief");
    cfgExeInp.type = "text";
    cfgExeInp.placeholder = "nInfer exe path (e.g. C:\\ninfer\\ninfer-serve.exe)";
    cfgExeInp.title = "Full path to ninfer-serve.exe (or its folder). Leave blank to auto-detect in C:\\ninfer, D:\\ninfer, or C:\\AI\\NInfer.";
    cfgExeInp.style.flex = "1 1 220px";
    const cfgModelFileInp = el("input", "h3e-writer-brief");
    cfgModelFileInp.type = "text";
    cfgModelFileInp.placeholder = "nInfer .ninfer file (or models folder / blank = auto)";
    cfgModelFileInp.title = "Full path to your .ninfer model file (e.g. Ternary-Bonsai-2-27B-ninfer-v3.ninfer), a models folder containing one, or blank to auto-pick from models\\.";
    cfgModelFileInp.style.flex = "1 1 240px";
    const cfgCtxSel = el("select", "h3e-select");
    cfgCtxSel.style.maxWidth = "160px";
    cfgCtxSel.title = "nInfer startup max context & KV reservation (--max-context / --kv-capacity). Lower to 16k-32k on tighter VRAM GPUs so workflow renders have room.";
    for (const [val, txt] of [
        [16384, "16k ctx (tight VRAM)"],
        [24576, "24k ctx"],
        [32768, "32k ctx (low VRAM)"],
        [49152, "48k ctx"],
        [65536, "64k ctx (default)"],
        [98304, "96k ctx"],
        [131072, "128k ctx"],
    ]) {
        const o = el("option", null, txt);
        o.value = String(val);
        cfgCtxSel.appendChild(o);
    }
    cfgCtxSel.value = "65536";
    cfgPathRow.append(el("span", "h3st-chips-lbl", "PATHS"), cfgExeInp, cfgModelFileInp, cfgCtxSel);
    cfgPathRow.hidden = true;

    writerCfgDrawer.append(cfgRow, cfgPathRow);

    // 3. Active Summary & Advisory Strip (Aspect Mix, Domain Clash, Best Length, × chips)
    const activeStrip = el("div", "h3st-row");

    // 4. Multi-Select Dials (Primary 8 + Toggleable Secondary 11 Tray)
    const dialControllers = {};
    const allMsels = [];
    const primaryGrid = el("div", "h3st-grid-primary");
    const secondaryGrid = el("div", "h3st-grid-primary");
    const secondaryDrawer = el("div", "h3st-drawer");
    secondaryDrawer.hidden = true;
    secondaryDrawer.appendChild(secondaryGrid);

    const fxTimingSel = el("select", "h3e-select");
    fxTimingSel.style.maxWidth = "145px";
    for (const [val, txt] of [["delayed_mid", "FX: Delayed Mid"], ["from_start", "FX: From Start"]]) {
        const o = el("option", null, txt);
        o.value = val;
        fxTimingSel.appendChild(o);
    }
    fxTimingSel.value = flavors.fx_timing || "delayed_mid";
    fxTimingSel.addEventListener("change", () => { flavors.fx_timing = fxTimingSel.value; persistFlavors(); });

    function closeAllPopovers(except = null) {
        for (const ms of allMsels) {
            if (ms !== except) ms.closePopover();
        }
    }

    function createMultiSelect(key, placeholder, defaultMode = "sequence", opts = {}) {
        const wrap = el("div", "h3e-msel");
        const btn = el("button", "h3e-msel-btn");
        btn.type = "button";
        const btnTxt = el("span", "h3e-msel-txt", placeholder);
        const btnBadge = el("span", "h3e-msel-badge");
        btnBadge.hidden = true;
        const btnCaret = el("span", "h3e-msel-caret", "▾");
        btn.append(btnTxt, btnBadge, btnCaret);

        const pop = el("div", "h3e-msel-pop");
        pop.hidden = true;

        const head = el("div", "h3e-msel-head");
        const search = el("input", "h3e-writer-brief h3e-msel-search");
        search.type = "text";
        search.placeholder = "Filter…";
        const randBtn = button("🎲", `Randomize ${key} cleanly`, () => {
            const cands = itemsData.filter((it) => !it.multi_hop_only && (aspectFilter === "all" || it.aspect_best === "either" || it.aspect_best === aspectFilter));
            if (!cands.length) return;
            const pick = cands[Math.floor(Math.random() * cands.length)];
            setValue(pick.id);
            renderActiveStrip();
        }, "h3e-btn h3e-msel-clear");

        let aspectFilter = "all";
        const aspBtn = button("All", "Filter options by aspect (All / 9:16 / 16:9)", () => {
            aspectFilter = aspectFilter === "all" ? "9:16" : (aspectFilter === "9:16" ? "16:9" : "all");
            aspBtn.textContent = aspectFilter === "all" ? "All" : aspectFilter;
            aspBtn.classList.toggle("h3e-on", aspectFilter !== "all");
            filterRows(search.value);
        }, "h3e-btn h3e-msel-mode");

        let mode = flavors.dial_modes?.[key] || defaultMode;
        const modeLabels = opts.allowSplit
            ? { sequence: "1→2", blend: "Blend", split: "S1/S2" }
            : { sequence: "1→2", blend: "Blend" };
        const modeCycle = opts.allowSplit ? ["sequence", "blend", "split"] : ["sequence", "blend"];
        const modeBtn = button(modeLabels[mode] || "1→2", "Cycle how multiple picks combine", () => {
            mode = modeCycle[(modeCycle.indexOf(mode) + 1) % modeCycle.length];
            flavors.dial_modes ??= {};
            flavors.dial_modes[key] = mode;
            modeBtn.textContent = modeLabels[mode] || mode;
            modeBtn.classList.toggle("h3e-on", mode !== "sequence");
            persistFlavors();
        }, "h3e-btn h3e-msel-mode");

        const clearBtn = button("Clear", "Clear selections on this dial", () => {
            setValue("");
            renderActiveStrip();
        }, "h3e-btn h3e-msel-clear");

        head.append(search, randBtn, aspBtn, modeBtn, clearBtn);
        const sub = el("div", "h3e-msel-sub", placeholder);
        const list = el("div", "h3e-msel-list");
        pop.append(head, sub, list);
        wrap.append(btn, pop);

        let itemsData = [];
        let itemMap = new Map();
        let rowEntries = [];
        let selectedIds = parseMultiValue(flavors[key]);

        function syncRows() {
            const selSet = new Set(selectedIds);
            for (const r of rowEntries) {
                const idx = selectedIds.indexOf(r.id);
                const checked = selSet.has(r.id);
                r.chk.checked = checked;
                r.row.classList.toggle("h3e-msel-checked", checked);
                r.ord.textContent = checked && selectedIds.length > 1 ? String(idx + 1) : "";
            }
            const first = selectedIds.length ? itemMap.get(selectedIds[0]) : null;
            if (!selectedIds.length) {
                btnTxt.textContent = placeholder;
                btnBadge.hidden = true;
                wrap.classList.remove("h3e-msel-active");
                sub.textContent = placeholder;
            } else {
                btnTxt.textContent = selectedIds.length === 1 ? (first?.label || selectedIds[0]) : `${selectedIds.length} selected (${first?.label || selectedIds[0]})`;
                btnBadge.textContent = String(selectedIds.length);
                btnBadge.hidden = selectedIds.length <= 1;
                wrap.classList.add("h3e-msel-active");
                sub.textContent = selectedIds.map((id) => itemMap.get(id)?.label || id).join(" · ");
            }
        }

        function filterRows(q) {
            const tok = String(q || "").trim().toLowerCase();
            for (const r of rowEntries) {
                const textOk = !tok || r.searchBlob.includes(tok);
                const aspOk = aspectFilter === "all" || r.item.aspect_best === "either" || r.item.aspect_best === aspectFilter;
                r.row.hidden = !(textOk && aspOk);
            }
            for (const g of list.querySelectorAll(".h3e-msel-grp")) {
                const grpName = g.dataset.grp || "";
                const anyVis = rowEntries.some((r) => r.group === grpName && !r.row.hidden);
                g.hidden = !anyVis;
            }
        }

        function setValue(val) {
            selectedIds = parseMultiValue(val);
            flavors[key] = serializeMultiValue(selectedIds);
            persistFlavors();
            syncRows();
        }

        function populate(items) {
            itemsData = Array.isArray(items) ? items : [];
            itemMap = new Map(itemsData.map((it) => [it.id, it]));
            rowEntries = [];
            list.textContent = "";

            const grouped = new Map();
            for (const it of itemsData) {
                const g = it.group || "General";
                if (!grouped.has(g)) grouped.set(g, []);
                grouped.get(g).push(it);
            }
            const frag = document.createDocumentFragment();
            for (const [grp, gItems] of grouped.entries()) {
                const gEl = el("div", "h3e-msel-grp", grp);
                gEl.dataset.grp = grp;
                frag.appendChild(gEl);
                for (const it of gItems) {
                    const row = el("label", "h3e-msel-item");
                    const chk = document.createElement("input");
                    chk.type = "checkbox";
                    const ord = el("span", "h3e-msel-ord");
                    const lbl = el("span", "h3e-msel-lbl", it.label || it.id);
                    row.title = [it.label, it.aspect_tip, it.duration_tip, it.multi_hop_only ? "Multi-hop Co-Pilot join camera" : ""].filter(Boolean).join("\n");
                    row.append(chk, ord, lbl);
                    if (it.aspect_best === "9:16" || it.aspect_best === "16:9") {
                        row.appendChild(el("span", `h3e-msel-tag asp-${it.aspect_best === "9:16" ? "916" : "169"}`, it.aspect_best));
                    }
                    if (it.duration_best && (key === "explicit" || key === "combat" || key === "camera" || key === "pose")) {
                        row.appendChild(el("span", "h3e-msel-tag dur-tag", it.duration_best));
                    }
                    chk.addEventListener("change", () => {
                        pushUndoSnapshot();
                        if (chk.checked) {
                            if (!selectedIds.includes(it.id)) selectedIds = [...selectedIds, it.id];
                        } else {
                            selectedIds = selectedIds.filter((x) => x !== it.id);
                        }
                        flavors[key] = serializeMultiValue(selectedIds);
                        persistFlavors();
                        syncRows();
                        renderActiveStrip();
                    });
                    rowEntries.push({
                        id: it.id,
                        item: it,
                        group: grp,
                        row,
                        chk,
                        ord,
                        searchBlob: `${it.label || ""} ${it.id} ${grp} ${it.domain || ""}`.toLowerCase(),
                    });
                    frag.appendChild(row);
                }
            }
            list.appendChild(frag);
            selectedIds = selectedIds.filter((id) => itemMap.has(id));
            syncRows();
        }

        function closePopover() {
            pop.hidden = true;
            wrap.classList.remove("h3e-msel-open");
        }

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const willOpen = pop.hidden;
            closeAllPopovers(willOpen ? api : null);
            pop.hidden = !willOpen;
            wrap.classList.toggle("h3e-msel-open", willOpen);
            if (willOpen) {
                pop.classList.remove("h3e-msel-right", "h3e-msel-up");
                pop.style.left = "";
                pop.style.right = "";
                pop.style.maxWidth = "";
                list.style.maxHeight = "";
                const rect = wrap.getBoundingClientRect();
                const container = wrap.closest(".r2-root, .h3e-root, .h3st-modal-box");
                const cRect = container?.getBoundingClientRect?.();
                const visLeft = Math.max(cRect ? cRect.left : 0, 0) + 8;
                const visRight = Math.min(cRect ? cRect.right : window.innerWidth, window.innerWidth) - 8;
                const visTop = Math.max(cRect ? cRect.top : 0, 0) + 8;
                const visBottom = Math.min(cRect ? cRect.bottom : window.innerHeight, window.innerHeight) - 8;
                const scale = (wrap.offsetWidth > 0 && rect.width > 0) ? (rect.width / wrap.offsetWidth) : 1;
                const availW = Math.max(200, Math.floor((visRight - visLeft) / scale));
                pop.style.maxWidth = `${Math.min(460, availW)}px`;
                const popRect = pop.getBoundingClientRect();
                if (rect.left + popRect.width > visRight) {
                    if (rect.right - popRect.width >= visLeft) {
                        pop.classList.add("h3e-msel-right");
                    } else {
                        const targetLeft = Math.max(visLeft, visRight - popRect.width);
                        pop.style.left = `${Math.round((targetLeft - rect.left) / scale)}px`;
                        pop.style.right = "auto";
                    }
                }
                const spaceBelow = visBottom - rect.bottom;
                const spaceAbove = rect.top - visTop;
                if (rect.bottom + popRect.height > visBottom && spaceAbove > spaceBelow) {
                    pop.classList.add("h3e-msel-up");
                    if (spaceAbove < popRect.height) {
                        list.style.maxHeight = `${Math.max(120, Math.floor((spaceAbove - 78) / scale))}px`;
                    }
                } else if (spaceBelow < popRect.height) {
                    list.style.maxHeight = `${Math.max(120, Math.floor((spaceBelow - 78) / scale))}px`;
                }
                search.focus();
            }
        });
        pop.addEventListener("click", (e) => e.stopPropagation());
        search.addEventListener("input", () => filterRows(search.value));

        const api = {
            wrap,
            populate,
            setValue,
            getSelected: () => selectedIds.slice(),
            getItem: (id) => itemMap.get(id),
            getItems: () => itemsData,
            closePopover,
        };
        allMsels.push(api);
        dialControllers[key] = api;
        return api;
    }

    for (const [k, ph] of PRIMARY_DIALS) {
        const ms = createMultiSelect(k, ph, "sequence", { allowSplit: k === "wardrobe" });
        primaryGrid.appendChild(ms.wrap);
    }
    for (const [k, ph] of SECONDARY_DIALS) {
        const ms = createMultiSelect(k, ph, k === "character" ? "split" : "sequence", { allowSplit: k === "character" });
        secondaryGrid.appendChild(ms.wrap);
    }
    secondaryGrid.appendChild(fxTimingSel);

    // 5. Toggle Bar for Optics Tray, Scripts Drawer, Clip->Beats Drawer & Quick Chips
    const toolRow = el("div", "h3st-row");
    const trayToggleBtn = button("▸ + Optics, Grade, Dance & Audio", "Toggle optics, color, FX, dance/pose, playbook & audio dials", () => {
        secondaryDrawer.hidden = !secondaryDrawer.hidden;
        updateTrayButton();
    });
    const scriptsToggleBtn = button("▤ Scripts", "Load clean-room SandTie showcase scripts", () => {
        const open = scriptsDrawer.hidden;
        scriptsDrawer.hidden = !open;
        clipDrawer.hidden = true;
        scriptsToggleBtn.classList.toggle("h3st-chip-on", open);
        clipToggleBtn.classList.remove("h3st-chip-on");
    });
    const clipToggleBtn = button("▶ Clip → Beats", "Extract timed beats from a video via 30-FPS OpenCV", () => {
        const open = clipDrawer.hidden;
        clipDrawer.hidden = !open;
        scriptsDrawer.hidden = true;
        clipToggleBtn.classList.toggle("h3st-chip-on", open);
        scriptsToggleBtn.classList.remove("h3st-chip-on");
        if (open) refreshStatus(false);
    });

    function updateTrayButton() {
        const secOn = SECONDARY_DIALS.filter(([k]) => parseMultiValue(flavors[k]).length > 0).length;
        const prefix = secondaryDrawer.hidden ? "▸ +" : "▾ Hide";
        trayToggleBtn.textContent = `${prefix} Optics, Grade, Dance & Audio${secOn ? ` (${secOn} on)` : ""}`;
        trayToggleBtn.classList.toggle("h3st-chip-on", !secondaryDrawer.hidden || secOn > 0);
    }

    function perfWeightOf(axis, val) {
        const rows = PERF_LEVEL_SPEC[axis] || [];
        const norm = normPerfVal(axis, val);
        const row = rows.find((r) => r[0] === norm) || rows[2];
        return row ? Number(row[2]) : 0.0;
    }

    function findUpstreamSteeringNode() {
        const g = node?.graph;
        if (!g || !Array.isArray(g._nodes)) return null;
        const seen = new Set();
        const stack = [node];
        while (stack.length) {
            const cur = stack.pop();
            if (!cur || seen.has(cur.id)) continue;
            seen.add(cur.id);
            if (cur !== node && cur.type === "HTCSteeringDials") return cur;
            for (const inp of cur.inputs || []) {
                if (inp?.link == null) continue;
                const lk = g.links?.[inp.link];
                const src = lk ? g.getNodeById?.(lk.origin_id) : null;
                if (src) stack.push(src);
            }
        }
        return g._nodes.find((n) => n?.type === "HTCSteeringDials") || null;
    }

    function syncSteeringNode({ announce = false } = {}) {
        const stNode = findUpstreamSteeringNode();
        if (!stNode) {
            if (announce) say("No HTCSteeringDials node found in graph — add one before MODEL to steer embeddings directly.", "hint");
            return false;
        }
        const motW = stNode.widgets?.find((w) => w.name === "motion");
        const expW = stNode.widgets?.find((w) => w.name === "expression");
        const enW = stNode.widgets?.find((w) => w.name === "energy");
        const sndW = stNode.widgets?.find((w) => w.name === "sound");
        const scW = stNode.widgets?.find((w) => w.name === "scope");
        const motV = perfWeightOf("motion", flavors.motion) * 0.5;
        const expV = perfWeightOf("expression", flavors.expression) * 0.5;
        const enV = perfWeightOf("energy", flavors.energy) * 0.5;
        const sndMap = { pure_bgm: -1.0, quiet_air: -0.5, auto: 0.0, foley: 1.0 };
        const sndV = sndMap[String(flavors.sound_mode || "auto").toLowerCase()] ?? 0.0;
        for (const [w, val] of [[motW, motV], [expW, expV], [enW, enV], [sndW, sndV], [scW, flavors.steering_scope]]) {
            if (!w || val === undefined) continue;
            w.value = val;
            try { w.callback?.(val, stNode.graph?.canvas, stNode); } catch (_) {}
        }
        stNode.graph?.setDirtyCanvas?.(true, true);
        if (announce) say(`Synced Motion=${motV >= 0 ? "+" : ""}${motV.toFixed(2)}, Expr=${expV >= 0 ? "+" : ""}${expV.toFixed(2)}, Energy=${enV >= 0 ? "+" : ""}${enV.toFixed(2)}, Sound=${sndV >= 0 ? "+" : ""}${sndV.toFixed(2)} onto HTCSteeringDials.`, "hint");
        return true;
    }

    const perfStepWidgets = {};
    const perfBox = el("div", "h3st-perf-box");
    const perfHead = el("div", "h3st-head");
    const perfTitle = el("span", "h3st-chips-lbl", "PERFORMANCE & STEERING DIALS");
    perfTitle.style.color = "var(--h3-text)";
    const bindSteerLbl = el("label", "h3st-sw");
    bindSteerLbl.title = "When enabled, Option A step dials automatically push scaled steering weights onto any HTCSteeringDials node in the graph";
    const bindSteerChk = document.createElement("input");
    bindSteerChk.type = "checkbox";
    bindSteerChk.checked = Boolean(flavors.steering_bind);
    bindSteerChk.addEventListener("change", () => {
        flavors.steering_bind = bindSteerChk.checked;
        persistFlavors();
        if (flavors.steering_bind) syncSteeringNode({ announce: true });
    });
    bindSteerLbl.append(bindSteerChk, el("span", null, "🎛 Auto-Sync Model Dials"));
    const syncSteerBtn = button("Sync → Steering Node", "Push current Motion / Energy / Expr levels onto an upstream HTCSteeringDials node", () => syncSteeringNode({ announce: true }), "h3e-btn");
    syncSteerBtn.style.padding = "2px 7px";
    syncSteerBtn.style.fontSize = "10.5px";
    const perfHeadR = el("div", "h3st-row");
    perfHeadR.append(bindSteerLbl, syncSteerBtn);
    perfHead.append(perfTitle, perfHeadR);

    const perfGrid = el("div", "h3st-perf-grid");
    const exprReadSel = el("select", "h3e-select");
    exprReadSel.title = "Facial acting flavor / read";
    exprReadSel.style.fontSize = "10.5px";
    exprReadSel.style.padding = "2px 5px";
    for (const [fid, flbl] of [
        ["auto", "Read: Auto"],
        ["stoic", "Read: Stoic / Cold"],
        ["warm", "Read: Warm / Sincere"],
        ["sly", "Read: Sly / Playful"],
        ["tense", "Read: Tense / Dread"],
        ["intense", "Read: Fierce / Intense"],
        ["sensual", "Read: Sensual / Intimate"],
    ]) {
        const o = el("option", null, flbl);
        o.value = fid;
        exprReadSel.appendChild(o);
    }
    exprReadSel.value = String(flavors.expr_read || "auto");
    exprReadSel.addEventListener("change", () => {
        flavors.expr_read = exprReadSel.value;
        persistFlavors();
    });

    function buildPerfCard(axis, title, withFlavorSel = false) {
        const card = el("div", "h3st-pcard");
        const top = el("div", "h3st-pcard-top");
        const tit = el("span", "h3st-ptit", title);
        const valSpan = el("span", "h3st-pval", "");
        top.append(tit, valSpan);

        const stepsRow = el("div", "h3st-psteps");
        const btns = [];
        for (const [id, lbl, wt, tip] of PERF_LEVEL_SPEC[axis]) {
            const b = button(lbl, `${title}: ${lbl} (${wt >= 0 ? "+" : ""}${wt}) — ${tip}`, () => {
                flavors[axis] = id;
                persistFlavors();
                syncPerfCards();
                if (flavors.steering_bind) syncSteeringNode();
            }, "h3e-btn h3st-pbtn");
            b.dataset.val = id;
            btns.push(b);
            stepsRow.appendChild(b);
        }
        const desc = el("div", "h3st-pdesc", "");
        card.append(top, stepsRow);
        if (withFlavorSel) card.appendChild(exprReadSel);
        else card.appendChild(desc);

        perfStepWidgets[axis] = { card, valSpan, btns, desc };
        return card;
    }

    perfGrid.append(
        buildPerfCard("motion", "MOTION"),
        buildPerfCard("energy", "ENERGY"),
        buildPerfCard("expression", "EXPRESSION", true),
        buildPerfCard("life", "LIFE"),
    );

    const chipWidgets = {};
    function buildChipGroup(key, title, choices) {
        const grp = el("div", "h3st-chips");
        grp.appendChild(el("span", "h3st-chips-lbl", title));
        const btns = [];
        for (const [val, lbl, tip] of choices) {
            const b = button(lbl, tip || `${title}: ${lbl}`, () => {
                flavors[key] = val;
                persistFlavors();
                syncChips();
                if ((key === "steering_scope" || key === "sound_mode") && flavors.steering_bind) syncSteeringNode();
            }, "h3e-btn");
            b.style.padding = "2px 6px";
            b.style.fontSize = "10.5px";
            b.dataset.val = val;
            btns.push(b);
            grp.appendChild(b);
        }
        chipWidgets[key] = btns;
        return grp;
    }

    function syncChips() {
        for (const [k, btns] of Object.entries(chipWidgets)) {
            const cur = String(flavors[k] || "");
            for (const b of btns) b.classList.toggle("h3st-chip-on", b.dataset.val === cur);
        }
    }

    function syncPerfCards() {
        normalizePerfFlavors(flavors);
        bindSteerChk.checked = Boolean(flavors.steering_bind);
        exprReadSel.value = String(flavors.expr_read || "auto");
        for (const [ax, ui] of Object.entries(perfStepWidgets)) {
            const cur = normPerfVal(ax, flavors[ax]);
            const rows = PERF_LEVEL_SPEC[ax];
            const found = rows.find((r) => r[0] === cur) || rows[2];
            const wt = found[2];
            ui.valSpan.textContent = `${found[1]} (${wt > 0 ? "+" : ""}${wt})`;
            ui.desc.textContent = found[3];
            ui.card.classList.toggle("is-non-zero", wt !== 0);
            for (const b of ui.btns) b.classList.toggle("h3st-chip-on", b.dataset.val === cur);
        }
    }

    const talkGrp = buildChipGroup("talk_mode", "TALK", [
        ["auto", "Auto", "Auto dialogue: speak only when brief quotes, talkstyle, or accent ask for speech"],
        ["talk_all", "All", "Speak across every beat/shot with natural voice rhythm"],
        ["quotes_only", "Quotes", "Speak ONLY explicit quoted lines in brief; keep unquoted scenes wordless"],
        ["silent", "Silent", "Strip all spoken <d> dialogue (keeps closed lips)"],
    ]);
    const soundGrp = buildChipGroup("sound_mode", "SOUND", [
        ["auto", "Auto", "Smart default: Pure Music (N/A) for dance with music; Ambience/room tone otherwise"],
        ["pure_bgm", "Pure BGM", "Force overall_soundscape: N/A & scrub noisy foley cues so music plays cleanly without footsteps or crunch"],
        ["quiet_air", "Quiet Air", "Soft narrowband indoor room air & minimal contact; suppresses loud crunch, impacts, and heavy breath"],
        ["foley", "Foley", "Keep crisp physical & environmental foley active in overall_soundscape (even on dance/MV presets)"],
    ]);
    const povGrp = buildChipGroup("pov", "POV", [
        ["off", "Off", "Standard third-person camera"],
        ["male", "M", "Male POV camera perspective"],
        ["female", "F", "Female POV camera perspective"],
    ]);
    const scopeGrp = buildChipGroup("steering_scope", "STEERING", [
        ["blocks_0_24 (voice safe)", "Blocks 0–24 (Voice Safe)", "Steer visual/motion blocks 0–24 while leaving blocks 25–49 untouched for clean voice & skin"],
        ["all_blocks", "All 50", "Shift refined prompt across all 50 DiT blocks (strongest for audio/sound dials)"],
    ]);
    const linkPrevLbl = el("label", "h3st-sw");
    linkPrevLbl.title = "Chain continuity from the active Script tab's previous hop into [Shot 1] (off by default so Quick Tie / Write stay isolated from old chains)";
    const linkPrevChk = document.createElement("input");
    linkPrevChk.type = "checkbox";
    linkPrevChk.checked = Boolean(flavors.link_prev_hop);
    linkPrevChk.addEventListener("change", () => {
        flavors.link_prev_hop = linkPrevChk.checked;
        persistFlavors();
    });
    linkPrevLbl.append(linkPrevChk, el("span", null, "⛓ Link Prev Hop"));
    syncPerfCards();
    syncChips();

    const auxRow = el("div", "h3st-aux-row");
    auxRow.append(talkGrp, soundGrp, povGrp, scopeGrp);
    if (!standalone) auxRow.appendChild(linkPrevLbl);
    perfBox.append(perfHead, perfGrid, auxRow);

    const spacerTool = el("span");
    spacerTool.style.flex = "1 1 auto";
    toolRow.append(trayToggleBtn, scriptsToggleBtn, clipToggleBtn, spacerTool);

    // 6. Scripts Drawer & Clip->Beats Drawer
    const scriptsDrawer = el("div", "h3st-drawer");
    scriptsDrawer.hidden = true;
    const scriptSel = el("select", "h3e-select");
    scriptSel.style.flex = "1 1 280px";
    const loadRawScriptBtn = button("Load Raw", "Paste selected script verbatim into Prompt block", () => loadOrAdaptScript(false));
    const adaptScriptBtn = button("Adapt to Refs & Dials", "Rebind <Subject N> and active Place/Style/Light/Colour onto this script", () => loadOrAdaptScript(true), "h3e-btn h3e-btn-accent");
    const scRow = el("div", "h3st-row");
    scRow.append(el("strong", null, "Curated Clean-Room Scripts:"), scriptSel, loadRawScriptBtn, adaptScriptBtn);
    scriptsDrawer.appendChild(scRow);

    const clipDrawer = el("div", "h3st-drawer");
    clipDrawer.hidden = true;
    const vidDropBox = el("div", "h3st-vdrop");
    vidDropBox.title = "Drop a video file (.mp4/.mov/.webm/.mkv) here or click to upload into input/h3_refs/";
    const vidUpInp = document.createElement("input");
    vidUpInp.type = "file";
    vidUpInp.accept = "video/*,.mp4,.mov,.webm,.mkv,.avi,.m4v";
    vidUpInp.hidden = true;
    const vidPickSel = el("select", "h3e-select");
    vidPickSel.style.maxWidth = "210px";
    vidPickSel.title = "Pick an existing video in input/h3_refs/ or input/";
    const vidUpBtn = button("+ Upload Video", "Upload a reference video into input/h3_refs/ for Video → Beats extraction", () => vidUpInp.click());
    const vidInput = el("input", "h3e-writer-brief");
    vidInput.type = "text";
    vidInput.placeholder = "drop video, pick from list, or type filename in input/ or h3_refs/…";
    const inSecInp = el("input", "h3e-writer-brief");
    inSecInp.type = "number";
    inSecInp.style.maxWidth = "68px";
    inSecInp.placeholder = "IN s";
    const outSecInp = el("input", "h3e-writer-brief");
    outSecInp.type = "number";
    outSecInp.style.maxWidth = "68px";
    outSecInp.placeholder = "OUT s";
    const extractBtn = button("Extract Beats", "Run 30-FPS OpenCV optical flow + jump-cut storyboard extractor", runVideoExtractor, "h3e-btn h3e-btn-accent");
    const extractedBadge = el("span", "h3st-pill", "No clip extracted");
    const clRow = el("div", "h3st-row");
    clRow.append(el("strong", null, "▶ Video → Beats:"), vidDropBox, vidPickSel, vidUpBtn, vidUpInp, vidInput, inSecInp, outSecInp, extractBtn, extractedBadge);
    clipDrawer.appendChild(clRow);

    let extractedVideoData = null;

    // 7. Prominent Reference Bible (open by default!)
    let bibleOpen = true;
    let bibleFilter = "all";
    let bibleQuery = "";
    let refBankItems = [];
    let refBankAudioFiles = [];
    let refBankVideoFiles = [];
    function notifyMediaPickerRefresh() {
        try {
            import("./media_picker.js").then((m) => m?.refresh?.()).catch(() => {});
        } catch (_) {}
    }

    function renderVidDropPreview(busyMsg = "") {
        vidDropBox.textContent = "";
        const vname = String(vidInput.value || "").trim();
        if (busyMsg) {
            vidDropBox.appendChild(el("span", "h3st-vdrop-hint", busyMsg));
            return;
        }
        if (!vname) {
            vidDropBox.appendChild(el("span", "h3st-vdrop-hint", "Drop video\nor click"));
            return;
        }
        const cleanBase = vname.replaceAll("\\", "/").split("/").pop();
        const vidEl = document.createElement("video");
        vidEl.src = `/view?filename=${encodeURIComponent(cleanBase)}&subfolder=h3_refs&type=input`;
        vidEl.muted = true;
        vidEl.loop = true;
        vidEl.playsInline = true;
        vidEl.preload = "metadata";
        vidEl.addEventListener("loadedmetadata", () => {
            try { vidEl.currentTime = 0.1; } catch (_) {}
        }, { once: true });
        vidEl.addEventListener("error", () => {
            // Try top-level input/ if not inside h3_refs/
            if (!vidEl.dataset.triedRoot) {
                vidEl.dataset.triedRoot = "1";
                vidEl.src = `/view?filename=${encodeURIComponent(cleanBase)}&type=input`;
                return;
            }
            vidEl.remove();
            vidDropBox.appendChild(el("span", "h3st-vdrop-hint", `▶ ${cleanBase.slice(0, 14)}`));
        });
        vidDropBox.appendChild(vidEl);
    }

    function fillVideoSelect(selectedName = "") {
        const chosen = String(selectedName || vidInput.value || "").trim();
        vidPickSel.textContent = "";
        const noneV = el("option", null, refBankVideoFiles.length ? "— Pick video —" : "— Drop or + Upload —");
        noneV.value = "";
        vidPickSel.appendChild(noneV);
        const seenV = new Set();
        for (const vfn of refBankVideoFiles) {
            if (!vfn || seenV.has(vfn)) continue;
            seenV.add(vfn);
            const o = el("option", null, `▶ ${vfn}`);
            o.value = vfn;
            vidPickSel.appendChild(o);
        }
        if (chosen && !seenV.has(chosen)) {
            const o = el("option", null, `▶ ${chosen}`);
            o.value = chosen;
            vidPickSel.appendChild(o);
        }
        vidPickSel.value = chosen;
        renderVidDropPreview();
    }

    async function uploadVideoClip(file) {
        if (!file) return;
        const ext = String(file.name || "").split(".").pop().toLowerCase();
        if (!["mp4", "mov", "webm", "mkv", "avi", "m4v"].includes(ext)) {
            return say(`${file.name} is not a supported video file (.mp4, .mov, .webm, .mkv, .avi, .m4v).`, "error");
        }
        const mb = (file.size / (1024 * 1024)).toFixed(1);
        say(`Uploading ${file.name} (${mb} MB) to input/h3_refs/…`, "hint");
        renderVidDropPreview("Uploading…");
        vidUpBtn.disabled = true;
        try {
            const fd = new FormData();
            fd.append("files", file, file.name);
            const upR = await fetch(UPLOAD_URL, { method: "POST", body: fd });
            const upJ = await upR.json().catch(() => ({}));
            const savedVid = upJ?.files?.[0]?.name;
            if (!upR.ok || !upJ?.ok || !savedVid) {
                throw new Error(upJ?.error || upJ?.skipped?.[0] || `Video upload failed (HTTP ${upR.status}).`);
            }
            if (!refBankVideoFiles.includes(savedVid)) {
                refBankVideoFiles = [savedVid, ...refBankVideoFiles];
            }
            vidInput.value = savedVid;
            extractedVideoData = null;
            fillVideoSelect(savedVid);
            extractedBadge.textContent = `Ready: ${savedVid}`;
            extractedBadge.className = "h3st-pill";
            notifyMediaPickerRefresh();
            say(`Uploaded ${savedVid} — click Extract Beats when ready.`, "hint");
        } catch (err) {
            renderVidDropPreview();
            say(String(err?.message || err), "error");
        } finally {
            vidUpBtn.disabled = false;
        }
    }

    vidDropBox.addEventListener("click", () => vidUpInp.click());
    vidDropBox.addEventListener("mouseenter", () => {
        const vEl = vidDropBox.querySelector("video");
        vEl?.play?.()?.catch?.(() => {});
    });
    vidDropBox.addEventListener("mouseleave", () => {
        const vEl = vidDropBox.querySelector("video");
        try { vEl?.pause?.(); } catch (_) {}
    });
    vidUpInp.addEventListener("change", async () => {
        const pickedVid = vidUpInp.files?.[0];
        vidUpInp.value = "";
        if (pickedVid) await uploadVideoClip(pickedVid);
    });
    vidPickSel.addEventListener("change", () => {
        vidInput.value = vidPickSel.value;
        extractedVideoData = null;
        renderVidDropPreview();
        if (vidPickSel.value) {
            extractedBadge.textContent = `Ready: ${vidPickSel.value}`;
            extractedBadge.className = "h3st-pill";
        } else {
            extractedBadge.textContent = "No clip extracted";
            extractedBadge.className = "h3st-pill";
        }
    });
    vidInput.addEventListener("input", () => {
        const typedV = vidInput.value.trim();
        if (extractedVideoData && extractedVideoData._video_file !== typedV) {
            extractedVideoData = null;
            extractedBadge.textContent = typedV ? `Ready: ${typedV}` : "No clip extracted";
            extractedBadge.className = "h3st-pill";
        }
        vidPickSel.value = refBankVideoFiles.includes(typedV) ? typedV : "";
        renderVidDropPreview();
    });
    for (const dropTarget of [clipDrawer, vidDropBox]) {
        dropTarget.addEventListener("dragover", (e) => {
            if (!e.dataTransfer?.types?.includes("Files")) return;
            e.preventDefault();
            e.stopPropagation();
            clipDrawer.classList.add("is-dragover");
            vidDropBox.classList.add("is-dragover");
        });
        dropTarget.addEventListener("dragleave", (e) => {
            if (dropTarget === clipDrawer && clipDrawer.contains(e.relatedTarget)) return;
            clipDrawer.classList.remove("is-dragover");
            vidDropBox.classList.remove("is-dragover");
        });
        dropTarget.addEventListener("drop", async (e) => {
            if (!e.dataTransfer?.files?.length) return;
            e.preventDefault();
            e.stopPropagation();
            clipDrawer.classList.remove("is-dragover");
            vidDropBox.classList.remove("is-dragover");
            await uploadVideoClip(e.dataTransfer.files[0]);
        });
    }
    fillVideoSelect("");

    const bibleBox = el("div", "h3st-bible");
    const bibleHead = el("div", "h3st-head");
    const bibleLeft = el("div", "h3st-row");
    const bibleToggleBtn = button("▾ 📖 Reference Bible", "Show or fold Reference Bible cards", () => {
        bibleOpen = !bibleOpen;
        renderReferenceBible();
    });
    const bibleWiredPills = el("div", "h3st-row");
    bibleLeft.append(bibleToggleBtn, bibleWiredPills);

    const bibleRight = el("div", "h3st-row");
    const syncRefModsBtn = button("↻ RefMods", "Sync & import all RefMods from models/refmods/ (and RefLoRAs) into Reference Bible", syncRefModsToBible);
    const castAllBtn = button("Cast Filtered → S1..S9", "Assign filtered Reference Bible cast onto Subject 1..N", castFilteredToRail);
    const saveRailBtn = button("Save Rail → Bible", "Import current rail subjects/plates/RefMods into your persistent Reference Bible", importRailToBible);
    const uploadInp = document.createElement("input");
    uploadInp.type = "file";
    uploadInp.accept = "image/*";
    uploadInp.hidden = true;
    uploadInp.addEventListener("change", async () => {
        const f = uploadInp.files?.[0];
        uploadInp.value = "";
        if (!f) return;
        await uploadAndScanFile(f);
    });
    const uploadBtn = button("+ Upload & Eye Scan", "Upload an image to h3_refs, run 2.5 MP Eye Scan, and save to Reference Bible", () => uploadInp.click());
    bibleRight.append(syncRefModsBtn, castAllBtn, saveRailBtn, uploadBtn, uploadInp);
    bibleHead.append(bibleLeft, bibleRight);

    const bibleBody = el("div", "h3st-shell");
    const bibleFilterRow = el("div", "h3st-row");
    const bibleSearchInp = el("input", "h3e-writer-brief");
    bibleSearchInp.type = "text";
    bibleSearchInp.style.flex = "1 1 160px";
    bibleSearchInp.placeholder = "Search Reference Bible (name, @tag, refmod, ethnicity, outfit)…";
    bibleSearchInp.addEventListener("input", () => {
        bibleQuery = bibleSearchInp.value;
        renderBibleCardsOnly();
    });
    const clearRailBtn = button("Clear Rail", "Clear wired refs in ref_plan", () => {
        setRefPlan(JSON.stringify({ refs: [], subjects: {} }));
        renderReferenceBible();
    });

    const bfBtns = {};
    for (const [fk, fl] of [["all", "All"], ["subject", "Cast"], ["place", "Plates"], ["prop", "Props"], ["refmod", "⬡ RefMods"]]) {
        const b = button(fl, `Show ${fl}`, () => {
            bibleFilter = fk;
            renderReferenceBible();
        });
        b.style.padding = "2px 7px";
        b.style.fontSize = "11px";
        bfBtns[fk] = b;
        bibleFilterRow.appendChild(b);
    }
    bibleFilterRow.append(bibleSearchInp, clearRailBtn);
    const bibleGrid = el("div", "h3st-bible-grid");
    bibleBody.append(bibleFilterRow, bibleGrid);
    bibleBox.append(bibleHead, bibleBody);

    function readRefPlanObj() {
        try {
            const d = JSON.parse(String(getRefPlan() || "") || "{}");
            return { refs: Array.isArray(d?.refs) ? d.refs : [], subjects: (d?.subjects && typeof d.subjects === "object") ? d.subjects : {} };
        } catch {
            return { refs: [], subjects: {} };
        }
    }

    function writeRefPlanObj(doc) {
        setRefPlan(JSON.stringify({ refs: doc.refs || [], subjects: doc.subjects || {} }));
    }

    function sameRefItem(r, item) {
        const rSrc = String(r?.source || "image").toLowerCase();
        const iSrc = String(item?.source || "image").toLowerCase();
        return rSrc === iSrc && String(r?.file || "").toLowerCase() === String(item?.file || "").toLowerCase();
    }

    function refmodRailFields(item) {
        if (String(item?.source || "image") !== "refmod") return {};
        const out = { source: "refmod" };
        if (item.strength != null && Number(item.strength) !== 1) {
            out.strength = Number(item.strength);
        }
        if (item.step_curve && item.step_curve !== "full") {
            out.step_curve = item.step_curve;
        }
        if (Array.isArray(item.members) && item.members.length) {
            out.members = item.members.slice();
        }
        return out;
    }

    function assignBibleItemToSlot(item, roleTarget) {
        const doc = readRefPlanObj();
        const wasSame = doc.refs.some((r) => sameRefItem(r, item) && (r.subject ? `S${r.subject}` : (r.retention === "prop" ? "Prop" : "Plate")) === roleTarget);
        const refs = doc.refs.filter((r) => !sameRefItem(r, item));
        const subjects = Object.assign({}, doc.subjects);

        // Clean up unused subject metadata for subjects no longer present on kept refs
        const cleanUnusedSubjects = (list) => {
            const liveSubs = new Set(list.map((r) => r.subject).filter((x) => x !== null && x !== undefined));
            for (const k of Object.keys(subjects)) {
                if (!liveSubs.has(Number(k))) delete subjects[k];
            }
        };

        if (roleTarget === "__remove__" || wasSame) {
            cleanUnusedSubjects(refs);
            doc.refs = refs;
            doc.subjects = subjects;
            writeRefPlanObj(doc);
            renderReferenceBible();
            return;
        }

        const usedSlots = new Set(refs.map((r) => Number(r.slot || 0)).filter((n) => n >= 1));
        const pickFreeSlot = (prefer = 0) => {
            if (prefer >= 1 && prefer <= 9 && !usedSlots.has(prefer)) return prefer;
            for (let n = 1; n <= 9; n++) if (!usedSlots.has(n)) return n;
            return refs.length + 1;
        };

        if (roleTarget === "Plate" || roleTarget === "Prop") {
            const slot = pickFreeSlot(0);
            refs.push({
                slot, tag: item.tag || "plate", file: item.file,
                subject: null, retention: roleTarget === "Prop" ? "prop" : "reference", desc: item.desc || "",
                ...refmodRailFields(item),
            });
        } else {
            const sn = Math.max(1, Math.min(9, Number(String(roleTarget).replace(/\D+/g, "")) || nextOpenSubjectSlot(refs)));
            const filtered = refs.filter((r) => Number(r.subject) !== sn);
            const usedAfter = new Set(filtered.map((r) => Number(r.slot || 0)).filter((n) => n >= 1));
            let slot = sn;
            if (usedAfter.has(slot)) {
                slot = 1;
                while (usedAfter.has(slot) && slot < 9) slot++;
            }
            filtered.push({
                slot, tag: item.tag || `subject${sn}`, file: item.file,
                subject: sn, retention: "fully_preserved", desc: item.desc || "",
                voice: item.voice || "",
                ...refmodRailFields(item),
            });
            subjects[sn] = {
                name: item.char_name || item.name || "",
                locked: item.locked || "",
                context: item.context || "",
            };
            filtered.sort((a, b) => Number(a.slot || 0) - Number(b.slot || 0));
            cleanUnusedSubjects(filtered);
            doc.refs = filtered;
            doc.subjects = subjects;
            writeRefPlanObj(doc);
            renderReferenceBible();
            return;
        }
        refs.sort((a, b) => Number(a.slot || 0) - Number(b.slot || 0));
        cleanUnusedSubjects(refs);
        doc.refs = refs;
        doc.subjects = subjects;
        writeRefPlanObj(doc);
        renderReferenceBible();
    }

    function nextOpenSubjectSlot(refsList) {
        const used = new Set((refsList || []).map((r) => Number(r.subject)).filter((n) => Number.isFinite(n) && n >= 1));
        for (let n = 1; n <= 9; n++) if (!used.has(n)) return n;
        return 9;
    }

    function castFilteredToRail() {
        const cast = refBankItems.filter((it) => {
            if (bibleFilter === "refmod" && it.source !== "refmod") return false;
            if (it.role !== "subject") return false;
            if (!bibleQuery) return true;
            return `${it.name} ${it.tag} ${it.file} ${it.desc}`.toLowerCase().includes(bibleQuery.toLowerCase());
        });
        if (!cast.length) return;
        const doc = { refs: [], subjects: {} };
        cast.slice(0, 9).forEach((it, idx) => {
            const sn = idx + 1;
            doc.refs.push({
                slot: sn, tag: it.tag || `subject${sn}`, file: it.file,
                subject: sn, retention: "fully_preserved", desc: it.desc || "", voice: it.voice || "",
                ...refmodRailFields(it),
            });
            doc.subjects[sn] = { name: it.char_name || it.name || "", locked: it.locked || "", context: it.context || "" };
        });
        writeRefPlanObj(doc);
        renderReferenceBible();
        say(`Cast ${Math.min(9, cast.length)} Reference Bible subject(s) onto S1..S${Math.min(9, cast.length)}.`, "hint");
    }

    let editingCardId = "";

    function renderBibleCardsOnly() {
        const doc = readRefPlanObj();
        const nextSub = nextOpenSubjectSlot(doc.refs);
        const byKeySlot = new Map();
        for (const r of doc.refs) {
            if (!r.file) continue;
            const k = `${String(r.source || "image").toLowerCase()}:${String(r.file).toLowerCase()}`;
            byKeySlot.set(k, r.subject ? `S${r.subject}` : (r.retention === "prop" ? "Prop" : "Plate"));
        }
        const q = bibleQuery.trim().toLowerCase();
        const visible = refBankItems.filter((it) => {
            if (bibleFilter === "refmod") {
                if (it.source !== "refmod") return false;
            } else if (bibleFilter !== "all" && it.role !== bibleFilter) {
                return false;
            }
            if (!q) return true;
            return `${it.name} ${it.tag} ${it.file} ${it.source || ""} ${it.refmod_role || ""} ${it.desc} ${it.voice}`.toLowerCase().includes(q);
        });

        bibleGrid.textContent = "";
        if (!visible.length) {
            const emptyMsg = el("div", "h3e-note", refBankItems.length ? "No Reference Bible items match this filter." : "No saved Reference Bible entries yet — click + Upload & Eye Scan, ↻ RefMods, or Save Rail → Bible.");
            bibleGrid.appendChild(emptyMsg);
            return;
        }
        const frag = document.createDocumentFragment();
        for (const it of visible.slice(0, 80)) {
            const isMod = it.source === "refmod";
            const itemKey = `${isMod ? "refmod" : "image"}:${String(it.file || "").toLowerCase()}`;
            const activeSlot = byKeySlot.get(itemKey) || "";
            const card = el("div", "h3st-bcard" + (activeSlot ? " h3st-bwired" : ""));
            const top = el("div", "h3st-btop");
            const thumbUrl = `${SANDTIE_THUMB_URL}?file=${encodeURIComponent(it.file)}&source=${isMod ? "refmod" : "image"}&w=128&v=${it.mtime || 1}`;
            if (isMod && it.refmod_has_looks === false) {
                top.appendChild(el("div", "h3st-bthumb", "⬡"));
            } else {
                const img = document.createElement("img");
                img.className = "h3st-bthumb";
                img.loading = "lazy";
                img.alt = it.name || it.tag;
                img.src = thumbUrl;
                if (isMod) {
                    img.addEventListener("error", () => {
                        const ph = el("div", "h3st-bthumb", "⬡");
                        img.replaceWith(ph);
                    });
                }
                top.appendChild(img);
            }
            const meta = el("div");
            meta.style.minWidth = "0";
            meta.style.flex = "1 1 auto";
            const nm = el("div", null, `${it.name || it.tag} `);
            nm.style.fontWeight = "700";
            nm.style.fontSize = "11.5px";
            nm.style.whiteSpace = "nowrap";
            nm.style.overflow = "hidden";
            nm.style.textOverflow = "ellipsis";
            const tagSp = el("span", null, `@${it.tag}`);
            tagSp.style.color = "var(--h3-muted)";
            tagSp.style.fontWeight = "400";
            nm.appendChild(tagSp);
            const metaBits = [it.role];
            if (isMod) {
                metaBits.push(`⬡ ${it.refmod_format || "refmod"}${it.refmod_tokens ? " · " + it.refmod_tokens + "t" : ""}`);
                if (it.strength != null && Number(it.strength) !== 1) metaBits.push(`×${Number(it.strength)}`);
                if (it.step_curve && it.step_curve !== "full") metaBits.push(it.step_curve);
            }
            if (it.voice) metaBits.push("♪ " + it.voice);
            const subMeta = el("div", null, metaBits.join(" · "));
            subMeta.style.fontSize = "10px";
            subMeta.style.color = "var(--h3-muted)";
            meta.append(nm, subMeta);
            top.appendChild(meta);
            if (isMod) {
                const rmPill = el("span", "h3st-pill", "⬡");
                rmPill.title = `RefMod (${it.file})`;
                top.appendChild(rmPill);
            }
            if (activeSlot) top.appendChild(el("span", "h3st-pill h3st-pill-accent", activeSlot));

            const desc = el("div", "h3st-bdesc", it.desc || (isMod ? `RefMod: ${it.file}` : "Pending Eye Scan…"));
            const acts = el("div", "h3st-row");
            if (it.role === "subject") {
                if (activeSlot && activeSlot.startsWith("S")) {
                    const rmBtn = button(`✓ ${activeSlot} ×`, `Wired as ${activeSlot} — click to remove from rail`, () => assignBibleItemToSlot(it, "__remove__"), "h3e-btn h3st-chip-on");
                    rmBtn.style.padding = "2px 6px";
                    rmBtn.style.fontSize = "10.5px";
                    acts.appendChild(rmBtn);
                } else {
                    const nextBtn = button(`+ S${nextSub}`, `Wire into next open slot (S${nextSub}) — supports S1 through S9`, () => assignBibleItemToSlot(it, `S${nextSub}`));
                    nextBtn.style.padding = "2px 6px";
                    nextBtn.style.fontSize = "10.5px";
                    acts.appendChild(nextBtn);
                }
                const slotSel = el("select", "h3e-select");
                slotSel.style.maxWidth = "56px";
                slotSel.style.padding = "2px 4px";
                slotSel.style.fontSize = "10.5px";
                slotSel.title = "Pick exact cast slot S1..S9";
                const phOpt = el("option", null, activeSlot || "S#");
                phOpt.value = "";
                slotSel.appendChild(phOpt);
                for (let n = 1; n <= 9; n++) {
                    const o = el("option", null, `S${n}`);
                    o.value = `S${n}`;
                    slotSel.appendChild(o);
                }
                slotSel.addEventListener("change", () => {
                    if (slotSel.value) assignBibleItemToSlot(it, slotSel.value);
                });
                acts.appendChild(slotSel);
            } else {
                const slotRole = it.role === "prop" ? "Prop" : "Plate";
                const cb = button(activeSlot === slotRole ? `✓ ${slotRole} ×` : `+ ${slotRole}`, activeSlot === slotRole ? `Remove ${slotRole} from rail` : `Wire as ${slotRole}`, () => assignBibleItemToSlot(it, activeSlot === slotRole ? "__remove__" : slotRole));
                cb.style.padding = "2px 6px";
                cb.style.fontSize = "10.5px";
                if (activeSlot === slotRole) cb.classList.add("h3st-chip-on");
                acts.appendChild(cb);
            }
            const scanBtn = button("👁", "Run 2.5 MP Eye Scan on this reference", () => scanBibleItem(it));
            scanBtn.style.padding = "2px 6px";
            scanBtn.style.fontSize = "10.5px";
            const editBtn = button("✎", "Edit Reference Bible name, @tag, role, voice & description", () => {
                editingCardId = editingCardId === it.id ? "" : it.id;
                renderBibleCardsOnly();
            });
            editBtn.style.padding = "2px 6px";
            editBtn.style.fontSize = "10.5px";
            if (editingCardId === it.id) editBtn.classList.add("h3st-chip-on");
            const delBtn = button("×", "Remove from Reference Bible", () => deleteBibleItem(it));
            delBtn.style.padding = "2px 6px";
            delBtn.style.fontSize = "10.5px";
            acts.append(scanBtn, editBtn, delBtn);

            card.append(top, desc, acts);

            if (editingCardId === it.id) {
                const ed = el("div", "h3st-shell");
                ed.style.paddingTop = "4px";
                ed.style.borderTop = "1px solid var(--h3-border-soft)";
                const nmInp = el("input", "h3e-writer-brief");
                nmInp.type = "text";
                nmInp.value = it.name || "";
                nmInp.placeholder = "Display name";
                const tagInp = el("input", "h3e-writer-brief");
                tagInp.type = "text";
                tagInp.value = it.tag || "";
                tagInp.placeholder = "@tag";
                const roleSel = el("select", "h3e-select");
                for (const rk of ["subject", "place", "prop"]) {
                    const o = el("option", null, rk);
                    o.value = rk;
                    roleSel.appendChild(o);
                }
                roleSel.value = it.role || "subject";
                const curVoice = String(it.voice || "").trim();
                const voiceSel = el("select", "h3e-select");
                voiceSel.style.flex = "1 1 150px";
                voiceSel.title = "Pick an audio clip (.mp3/.wav/.flac/.ogg/.m4a) from input/h3_refs/";
                const voiceInp = el("input", "h3e-writer-brief");
                voiceInp.type = "text";
                voiceInp.style.flex = "1 1 120px";
                voiceInp.value = curVoice;
                voiceInp.placeholder = "or type voice filename";
                const audioPrev = document.createElement("audio");
                audioPrev.controls = true;
                audioPrev.style.height = "26px";
                audioPrev.style.maxWidth = "210px";
                const syncAudioPrev = (vname) => {
                    const clean = String(vname || "").trim();
                    if (clean) {
                        audioPrev.hidden = false;
                        audioPrev.src = `/view?filename=${encodeURIComponent(clean)}&subfolder=h3_refs&type=input`;
                    } else {
                        audioPrev.hidden = true;
                        audioPrev.removeAttribute("src");
                    }
                };
                const fillVoiceSelect = (selectedName) => {
                    const chosen = String(selectedName || "").trim();
                    voiceSel.textContent = "";
                    const noneOpt = el("option", null, "— No voice —");
                    noneOpt.value = "";
                    voiceSel.appendChild(noneOpt);
                    const seen = new Set();
                    for (const fn of refBankAudioFiles) {
                        if (!fn || seen.has(fn)) continue;
                        seen.add(fn);
                        const o = el("option", null, `♪ ${fn}`);
                        o.value = fn;
                        voiceSel.appendChild(o);
                    }
                    if (chosen && !seen.has(chosen)) {
                        const o = el("option", null, `♪ ${chosen}`);
                        o.value = chosen;
                        voiceSel.appendChild(o);
                    }
                    voiceSel.value = chosen;
                    syncAudioPrev(chosen);
                };
                fillVoiceSelect(curVoice);
                voiceSel.addEventListener("change", () => {
                    voiceInp.value = voiceSel.value;
                    syncAudioPrev(voiceSel.value);
                });
                voiceInp.addEventListener("input", () => {
                    const typed = voiceInp.value.trim();
                    if (refBankAudioFiles.includes(typed) || !typed) {
                        voiceSel.value = typed;
                    }
                    syncAudioPrev(typed);
                });

                const voiceUpInp = document.createElement("input");
                voiceUpInp.type = "file";
                voiceUpInp.accept = "audio/*,.mp3,.wav,.flac,.ogg,.m4a,.aac";
                voiceUpInp.hidden = true;
                voiceUpInp.addEventListener("change", async () => {
                    const vf = voiceUpInp.files?.[0];
                    voiceUpInp.value = "";
                    if (!vf) return;
                    try {
                        say(`Uploading voice ${vf.name}…`, "hint");
                        const fd = new FormData();
                        fd.append("files", vf, vf.name);
                        const upR = await fetch(UPLOAD_URL, { method: "POST", body: fd });
                        const upJ = await upR.json();
                        const savedAudio = upJ?.files?.[0]?.name;
                        if (!upR.ok || !upJ?.ok || !savedAudio) {
                            return say(upJ?.error || "Audio upload failed.", "error");
                        }
                        if (!refBankAudioFiles.includes(savedAudio)) {
                            refBankAudioFiles = [savedAudio, ...refBankAudioFiles];
                        }
                        voiceInp.value = savedAudio;
                        fillVoiceSelect(savedAudio);
                        notifyMediaPickerRefresh();
                        say(`Uploaded ${savedAudio} — click Save to store on card.`, "hint");
                    } catch (err) {
                        say(String(err), "error");
                    }
                });
                const voiceUpBtn = button("+ Audio", "Upload an .mp3 / .wav / .flac voice reference into h3_refs/", () => voiceUpInp.click());

                const descInp = el("textarea", "h3e-json");
                descInp.rows = 2;
                descInp.value = it.desc || "";

                let strInp = null;
                let curveSel = null;
                if (isMod) {
                    strInp = el("input", "h3e-writer-brief");
                    strInp.type = "number";
                    strInp.min = "0";
                    strInp.max = "3";
                    strInp.step = "0.05";
                    strInp.style.maxWidth = "68px";
                    strInp.title = "RefMod strength (default 1.0)";
                    strInp.value = String(it.strength ?? 1.0);
                    curveSel = el("select", "h3e-select");
                    curveSel.style.maxWidth = "115px";
                    curveSel.title = "RefMod per-step denoising curve";
                    for (const sc of ["full", "early_lock", "late_detail", "fade", "mid_peak"]) {
                        const o = el("option", null, sc);
                        o.value = sc;
                        curveSel.appendChild(o);
                    }
                    curveSel.value = it.step_curve || "full";
                }

                const saveCardBtn = button("Save", "Save changes to Reference Bible (also updates wired rail rows)", async () => {
                    const nextName = nmInp.value.trim();
                    const nextTag = tagInp.value.trim().replace(/^@/, "");
                    const nextRole = roleSel.value;
                    const nextVoice = (voiceInp.value.trim() || voiceSel.value || "").trim();
                    const nextDesc = descInp.value.trim();
                    const nextStrength = strInp ? (Number(strInp.value) || 1.0) : undefined;
                    const nextCurve = curveSel ? (curveSel.value || "full") : undefined;
                    const r = await fetch(SANDTIE_REFBANK_URL, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            action: "save",
                            item: {
                                id: it.id, file: it.file, source: it.source || "image",
                                name: nextName,
                                char_name: nextName.split(" ")[0],
                                tag: nextTag,
                                role: nextRole, voice: nextVoice, desc: nextDesc,
                                ...(isMod ? { strength: nextStrength, step_curve: nextCurve } : {}),
                            },
                        }),
                    });
                    const j = await r.json();
                    if (j.ok) {
                        refBankItems = j.items || [];
                        if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
                        // Keep any already-wired rail row in sync immediately so the user never has to re-wire or visit Ref Rail.
                        const doc = readRefPlanObj();
                        let syncedRail = false;
                        for (const row of doc.refs) {
                            if (sameRefItem(row, it)) {
                                row.voice = nextVoice;
                                if (nextDesc) row.desc = nextDesc;
                                if (nextTag) row.tag = nextTag;
                                if (isMod) {
                                    row.source = "refmod";
                                    if (nextStrength !== 1) row.strength = nextStrength;
                                    else delete row.strength;
                                    if (nextCurve && nextCurve !== "full") row.step_curve = nextCurve;
                                    else delete row.step_curve;
                                }
                                if (row.subject && doc.subjects?.[row.subject]) {
                                    doc.subjects[row.subject].name = (nextName.split(" ")[0]) || doc.subjects[row.subject].name || "";
                                }
                                syncedRail = true;
                            }
                        }
                        if (syncedRail) writeRefPlanObj(doc);
                        editingCardId = "";
                        renderReferenceBible();
                        say(`Updated ${nextName || it.file}${syncedRail ? " (+ synced rail)" : ""}.`, "hint");
                    }
                }, "h3e-btn h3e-btn-accent");
                const r1 = el("div", "h3st-row");
                r1.append(nmInp, tagInp, roleSel);
                if (strInp && curveSel) r1.append(strInp, curveSel);
                const r2 = el("div", "h3st-row");
                r2.append(voiceSel, voiceUpBtn, voiceUpInp, voiceInp, audioPrev, saveCardBtn);
                ed.append(r1, descInp, r2);
                card.appendChild(ed);
            }

            frag.appendChild(card);
        }
        bibleGrid.appendChild(frag);
    }

    function renderReferenceBible() {
        const doc = readRefPlanObj();
        bibleToggleBtn.textContent = `${bibleOpen ? "▾" : "▸"} 📖 Reference Bible (${refBankItems.length} Saved)`;
        bibleToggleBtn.classList.toggle("h3st-chip-on", bibleOpen);
        bibleBody.hidden = !bibleOpen;
        bibleWiredPills.textContent = "";
        for (const r of doc.refs) {
            if (!r.file) continue;
            const modMark = r.source === "refmod" ? "⬡ " : "";
            const badgeLbl = r.subject ? `${modMark}S${r.subject}: @${r.tag} ×` : `${modMark}${r.retention === "prop" ? "Prop" : "Plate"}: @${r.tag} ×`;
            const pBtn = button(badgeLbl, `Click to unassign @${r.tag}`, () => assignBibleItemToSlot({ file: r.file, source: r.source || "image" }, "__remove__"), "h3st-pill h3st-pill-accent");
            pBtn.style.cursor = "pointer";
            bibleWiredPills.appendChild(pBtn);
        }
        const counts = { all: refBankItems.length, subject: 0, place: 0, prop: 0, refmod: 0 };
        for (const it of refBankItems) {
            counts[it.role] = (counts[it.role] || 0) + 1;
            if (it.source === "refmod") counts.refmod += 1;
        }
        for (const [fk, b] of Object.entries(bfBtns)) {
            const lbl = fk === "all" ? "All" : (fk === "subject" ? "Cast" : (fk === "place" ? "Plates" : (fk === "prop" ? "Props" : "⬡ RefMods")));
            b.textContent = `${lbl} (${counts[fk] || 0})`;
            b.classList.toggle("h3st-chip-on", bibleFilter === fk);
        }
        if (bibleOpen) renderBibleCardsOnly();
    }

    async function syncRefModsToBible() {
        try {
            say("Scanning models/refmods/ & RefLoRAs into Reference Bible…", "hint");
            const r = await fetch(SANDTIE_REFBANK_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "sync_refmods" }),
            });
            const j = await r.json();
            if (!j.ok) return say(j.error || "RefMod sync failed.", "error");
            refBankItems = j.items || [];
            if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
            bibleOpen = true;
            renderReferenceBible();
            const nMods = refBankItems.filter((x) => x.source === "refmod").length;
            say(`Synced ${nMods} RefMod(s) into Reference Bible (${refBankItems.length} total).`, "hint");
        } catch (err) {
            say(String(err), "error");
        }
    }

    async function importRailToBible() {
        const r = await fetch(SANDTIE_REFBANK_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "import_rail", ref_plan: getRefPlan(), voice_files: getVoiceFiles() }),
        });
        const j = await r.json();
        if (j.ok) {
            refBankItems = j.items || [];
            if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
            renderReferenceBible();
            say(`Saved rail references into Reference Bible (${refBankItems.length} total).`, "hint");
        }
    }

    async function scanBibleItem(item) {
        say(`Eye-Scanning ${item.file} at 2.5 MP…`, "hint");
        const r = await fetch(SANDTIE_REFBANK_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "scan", id: item.id, file: item.file, source: item.source || "image", role: item.role, auto_wake: Boolean(flavors.wake_writer) }),
        });
        const j = await r.json();
        if (!j.ok) return say(j.error || "Eye Scan failed", "error");
        refBankItems = j.items || [];
        if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
        renderReferenceBible();
        say(`Eye Scan updated ${item.name || item.file}.`, "hint");
    }

    async function deleteBibleItem(item) {
        const r = await fetch(SANDTIE_REFBANK_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "delete", id: item.id, file: item.file, source: item.source || "image" }),
        });
        const j = await r.json();
        if (j.ok) {
            refBankItems = j.items || [];
            if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
            renderReferenceBible();
        }
    }

    async function uploadAndScanFile(file) {
        const fd = new FormData();
        fd.append("file", file, file.name);
        const upRes = await fetch(UPLOAD_URL, { method: "POST", body: fd });
        const upJson = await upRes.json();
        const savedName = upJson?.files?.[0]?.name;
        if (!savedName) return say(upJson?.error || "Upload failed", "error");
        notifyMediaPickerRefresh();
        say(`Uploaded ${savedName} — running 2.5 MP Eye Scan…`, "hint");
        const r = await fetch(SANDTIE_REFBANK_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "scan", file: savedName, role: "auto", auto_wake: Boolean(flavors.wake_writer) }),
        });
        const j = await r.json();
        if (j.ok) {
            refBankItems = j.items || [];
            if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
            bibleOpen = true;
            renderReferenceBible();
            say(`Added ${savedName} to Reference Bible.`, "hint");
        } else {
            say(j.error || "Upload succeeded, scan failed.", "error");
        }
    }

    // 8. Primary Action Bar + Block Tools + Telemetry
    let activeAbortCtrl = null;
    const fastBtn = button("⚡ Quick Tie (1-Pass)", "1-pass instant write using all active SandTie dials & Eye Scan", () => runSandTie("fast"), "h3e-btn h3e-btn-accent");
    const skelBtn = button("◩ Skeleton (0 VRAM)", "Build Shot-Tree storyboard ([Shot N] + weighted micro-beats) on CPU with zero LLM/VRAM usage", () => runSandTie("skeleton"));
    const cpuBtn = button("◩ CPU Tie", "Assemble instant complete H3 prompt on CPU with zero VRAM usage", () => runSandTie("cpu"));
    const freshDlgBtn = button("❝ Fresh Dialogue", "Rewrite spoken <d> lines while keeping physical pose/hands locked", () => runSandTie("dialogue"));
    const copyBtn = button("Copy", "Copy Prompt block to clipboard", async () => {
        if (!blockBox.value.trim()) return;
        try { await navigator.clipboard.writeText(blockBox.value); say("Copied prompt block to clipboard.", "hint"); } catch (_) {}
    });
    function resetExtractedClipState() {
        extractedVideoData = null;
        const curVid = String(vidInput.value || "").trim();
        extractedBadge.textContent = curVid ? `Ready: ${curVid}` : "No clip extracted";
        extractedBadge.className = "h3st-pill";
    }
    const clearPlanBtn = button("Clear", "Clear Storyboard field (use Undo to restore)", () => {
        if (!planBox.value && !extractedVideoData) return;
        pushUndoSnapshot();
        planBox.value = "";
        resetExtractedClipState();
        saveDraft();
        say("Cleared Storyboard (click Undo to restore).", "hint");
    });
    const clearBlockBtn = button("Clear", "Clear Prompt block (use Undo to restore)", () => {
        if (!blockBox.value) return;
        pushUndoSnapshot();
        blockBox.value = "";
        saveDraft();
        updateTelemetry();
        say("Cleared Prompt block (click Undo to restore).", "hint");
    });
    const clearBothBtn = button("✕ Clear Both", "Clear both Storyboard and Prompt block (use Undo to restore)", () => {
        if (!planBox.value && !blockBox.value && !extractedVideoData) return;
        pushUndoSnapshot();
        planBox.value = "";
        blockBox.value = "";
        resetExtractedClipState();
        saveDraft();
        updateTelemetry();
        say("Cleared Storyboard & Prompt block (click Undo to restore).", "hint");
    });
    const undoBtn = button("Undo", "Restore previous brief / storyboard / prompt / dials snapshot", () => {
        const prev = undoStack.pop();
        if (!prev) return;
        briefEl.value = prev.brief;
        planBox.value = prev.plan;
        blockBox.value = prev.block;
        try { Object.assign(flavors, JSON.parse(prev.flavors)); } catch (_) {}
        syncAllWidgets();
        saveDraft();
        syncBlockToSimplePrompt(blockBox.value);
        syncUndoBtn();
    });
    if (!standalone) {
        blockBox.addEventListener("input", () => syncBlockToSimplePrompt(blockBox.value));
    }
    function syncUndoBtn() {
        undoBtn.disabled = undoStack.length === 0;
        undoBtn.textContent = undoStack.length ? `Undo (${undoStack.length})` : "Undo";
    }
    syncUndoBtn();

    const abortBtn = button("■ Abort", "Cancel active writer request", () => {
        if (activeAbortCtrl) { activeAbortCtrl.abort(); activeAbortCtrl = null; say("Writer request aborted.", "hint"); }
    });
    abortBtn.hidden = true;

    const telemetryPill = el("span", "h3st-pill", "0s · 0b · 0w · 0/7000c");

    function updateTelemetry() {
        const txt = String(blockBox.value || "").trim();
        const shots = (txt.match(/\[\s*Shot\s+\d+\s*\]/gi) || []).length;
        const beats = (txt.match(/\bAt\s+\d+:\d+/gi) || []).length;
        const dlgs = (txt.match(/<d>/gi) || []).length;
        const words = txt ? txt.split(/\s+/).length : 0;
        const chars = txt.length;
        telemetryPill.textContent = `${shots}s · ${beats}b · <d>${dlgs} · ${words}w · ${chars}/7000c`;
        telemetryPill.className = "h3st-pill" + (chars > 7000 ? " h3st-pill-warn" : "");
    }
    blockBox.addEventListener("input", updateTelemetry);
    updateTelemetry();

    // 9. Combos & Smart Roll Helpers
    function refreshComboSelect() {
        comboSel.textContent = "";
        const ph = el("option", null, `Combos (${BUILTIN_DIAL_COMBOS.length} Built-In)…`);
        ph.value = "";
        comboSel.appendChild(ph);
        let userList = [];
        try { userList = JSON.parse(localStorage.getItem("h3_sandtie_user_combos") || "[]"); } catch {}
        if (userList.length) {
            const ug = document.createElement("optgroup");
            ug.label = "Saved User Combos";
            for (const c of userList) {
                const o = el("option", null, c.label);
                o.value = c.id;
                ug.appendChild(o);
            }
            comboSel.appendChild(ug);
        }
        const bg = document.createElement("optgroup");
        bg.label = "SandTie Built-In Combos";
        for (const c of BUILTIN_DIAL_COMBOS) {
            const o = el("option", null, c.label);
            o.value = c.id;
            bg.appendChild(o);
        }
        comboSel.appendChild(bg);
    }

    function applyComboValues(vals) {
        pushUndoSnapshot();
        for (const k of ALL_DIAL_KEYS) flavors[k] = "";
        flavors.motion = "natural";
        flavors.energy = "steady";
        flavors.expression = "natural";
        flavors.expr_read = "auto";
        flavors.life = "natural";
        Object.assign(flavors, vals || {});
        if (vals && !("motion" in vals) && ("energy" in vals)) {
            flavors.motion = normPerfVal("motion", vals.energy);
        }
        normalizePerfFlavors(flavors);
        flavors.dial_modes = Object.assign({}, vals?.dial_modes || {});
        persistFlavors();
        syncAllWidgets();
        if (flavors.steering_bind) syncSteeringNode();
    }

    comboSel.addEventListener("change", () => {
        const cid = comboSel.value;
        if (!cid) return;
        let userList = [];
        try { userList = JSON.parse(localStorage.getItem("h3_sandtie_user_combos") || "[]"); } catch {}
        const found = [...userList, ...BUILTIN_DIAL_COMBOS].find((c) => c.id === cid);
        if (found) applyComboValues(found.values);
    });

    function saveUserCombo() {
        const name = window.prompt("Name this SandTie dial combo:", "My Custom Rig");
        if (!name || !name.trim()) return;
        let userList = [];
        try { userList = JSON.parse(localStorage.getItem("h3_sandtie_user_combos") || "[]"); } catch {}
        const vals = {};
        for (const k of ALL_DIAL_KEYS) if (flavors[k]) vals[k] = flavors[k];
        vals.talk_mode = flavors.talk_mode;
        vals.sound_mode = flavors.sound_mode;
        vals.motion = flavors.motion;
        vals.energy = flavors.energy;
        vals.expression = flavors.expression;
        vals.expr_read = flavors.expr_read;
        vals.life = flavors.life;
        vals.pov = flavors.pov;
        vals.dial_modes = Object.assign({}, flavors.dial_modes || {});
        userList.unshift({ id: `user_${Date.now()}`, label: name.trim(), values: vals });
        localStorage.setItem("h3_sandtie_user_combos", JSON.stringify(userList.slice(0, 40)));
        refreshComboSelect();
    }

    function deleteUserCombo() {
        const cid = comboSel.value;
        if (!cid || !cid.startsWith("user_")) return;
        let userList = [];
        try { userList = JSON.parse(localStorage.getItem("h3_sandtie_user_combos") || "[]"); } catch {}
        userList = userList.filter((c) => c.id !== cid);
        localStorage.setItem("h3_sandtie_user_combos", JSON.stringify(userList));
        refreshComboSelect();
    }

    function domainsMatch(a, b) {
        const da = (a || "general").toLowerCase();
        const db = (b || "general").toLowerCase();
        if (da === db || da === "general" || db === "general") return true;
        if (da === "bedroom") return db === "sofa_lounge" || db === "mirror_vanity" || db === "bdsm_dom";
        if (db === "bedroom") return da === "sofa_lounge" || da === "mirror_vanity" || da === "bdsm_dom";
        return false;
    }

    function runSurpriseRoll() {
        pushUndoSnapshot();
        const aspSpec = parseAspectSpec(getAspect());
        const targetAsp = aspSpec.bucket;
        const fitAsp = (it) => targetAsp === "either" || it.aspect_best === "either" || it.aspect_best === targetAsp;
        const refPlanObj = readRefPlanObj();
        const wiredSubjs = new Set(
            (refPlanObj.refs || []).map((r) => Number(r.subject || 0)).filter((n) => n > 0),
        );
        const nSubj = Math.max(1, wiredSubjs.size || Object.keys(refPlanObj.subjects || {}).length || 1);

        const itemBlob = (it) => `${it?.id || ""} ${it?.label || ""} ${it?.group || ""}`.toLowerCase();
        const isNsfwOpt = (it) => {
            const d = String(it?.domain || "").toLowerCase();
            if (["bedroom", "bdsm_dom", "gloryhole", "wet_shower", "wet_tub"].includes(d)) return true;
            return /(?:^|[^a-z0-9])(?:nude|partial|fetish|boudoir|erotic|intimate|climax|filthy|dirty|praise|mommy|domme|submissive|lingerie|afterglow|pillow|gasp|whimper|overstim|sensual|strip[_ ]?club|casting[_ ]?studio|love[_ ]?hotel|multi_position_3cut_intimate|bare_legs|bare[_ ]?breasts|bare[_ ]?back|micro_string)(?:$|[^a-z0-9])/.test(itemBlob(it));
        };
        const isMultiOpt = (it) => {
            if (Number(it?.people || 0) >= 2) return true;
            return /(?:duet|two_shot|two[- ]subject|s1[_ ]?(?:vs|\+|to)[_ ]?s2|s1_s2|tag[_-]?team|split_partner|both_partners|ensemble|s1_s9|lesbian|pegging|2-subject)/.test(itemBlob(it));
        };
        const isEnsembleOpt = (it) => Number(it?.people || 0) >= 3 || /ensemble|s1_s9|squad/.test(itemBlob(it));
        const isSoloOnlyOpt = (it) => Number(it?.people || 0) === 1 || /(?:^|[^a-z0-9])(?:solo|one[- _]person|masturb\w*|dildo)(?:$|[^a-z0-9])/.test(itemBlob(it));
        const castFit = (it) => {
            if (!it) return false;
            if (/^split_partner_/i.test(it.id || "")) return false;
            if (nSubj <= 1) return !isMultiOpt(it) && !isEnsembleOpt(it);
            if (nSubj === 2) return !isEnsembleOpt(it) && !isSoloOnlyOpt(it);
            return !isSoloOnlyOpt(it);
        };
        const isAnimeOpt = (it) => /(?:anime|sakuga|manhwa|2d_|manga|makoto|ghibli|trigger|ufotable|arcane|edgerunner|hollow_purple|black_flash|rasengan|susanoo|senbonzakura|water_breathing|hinokami|thunder_clap|moon_breathing|beast_breathing|mist_breathing|domain_void|getsu|bankai|amaterasu|gear_fifth|chainsaw|conquerors_haki)/.test(itemBlob(it));
        const isWuxiaOpt = (it) => /(?:wuxia|samurai|iaido|katana|bamboo|shinobi|kunoichi|shihakusho|kimono|shamisen|dojo)/.test(itemBlob(it));
        const isCyberOpt = (it) => /(?:cyber|neon|holo|mantis|sandevistan|starship|scifi|biolab|mech|laser|hud|plasma)/.test(itemBlob(it));
        const isDayPlace = (it) => /(?:morning|sunlit|amalfi|pacific_wet_sand|mediterranean|parking_golden|ring_sunlight|ballet_rehearsal|scandinavian|pine_forest_sunbeams|stoop_golden|private_gym|sunpad_mediterranean|infinity_courtyard|simple_enclosed|plain_soft_natural|real_lived_in|real_attic|real_small_urban|real_everyday_kitchen)/.test(itemBlob(it));
        const isNightNeonPlace = (it) => /(?:neon|night|midnight|hongdae|izakaya|laundromat|bowling|ramen|proscenium|strip_club|backstage|shibuya|lantern|subway|obsidian|foundry|throne|vault|real_night_bedside|real_cheap_motel|real_dim_apartment)/.test(itemBlob(it));
        const lightMatchesPlace = (lt, pl) => {
            if (!lt) return false;
            const lb = itemBlob(lt);
            if (/refrigerator_door|police_red_blue|bioluminescent/.test(lb)) return false;
            if (pl && isDayPlace(pl)) {
                return /(?:soft_natural|sunset|golden|dappled|overcast|three_point|butterfly|high_key|north_window|raking)/.test(lb);
            }
            if (pl && isNightNeonPlace(pl)) {
                return /(?:neon|cyber|strobe|kpop_concert|ringlight|ring_beauty|laser|puddle|chiaroscuro|blue_hour|moonlight|vip_amber|red_velvet|underground_cage|fluorescent|practical|firelight)/.test(lb);
            }
            return !/(?:underground_cage_halide|paparazzi_red_carpet)/.test(lb);
        };
        const camIsSafeIntimate = (it) => !/(?:drone|bird_cam|pet_cam|cctv|bodycam|sandevistan|blade_tip|hip_locked|car_chasing|trunk_shot|conveyor|pov_helmet|fake_webcam|earth_zoom|road_rush|combat)/.test(itemBlob(it));
        const camIsSafeCinema = (it) => !/(?:pet_cam|cctv|bodycam|sandevistan|blade_tip|hip_locked|pov_helmet|combat|selfie_high|3cut_intimate|contour_s_curve|barrel_roll|under_glass)/.test(itemBlob(it));

        const pickedDoms = [];
        const domAllOk = (it) => pickedDoms.every((d) => domainsMatch(d, it?.domain));
        const pickOne = (k, pred = null) => {
            const arr = (dialControllers[k]?.getItems() || []).filter((it) => !it.multi_hop_only && fitAsp(it) && castFit(it) && (!pred || pred(it)));
            return arr.length ? arr[Math.floor(Math.random() * arr.length)] : null;
        };
        const pickPref = (k, strictPred, fallbackPred = null) => pickOne(k, strictPred) || (fallbackPred ? pickOne(k, fallbackPred) : null);
        const regDom = (it) => { if (it?.domain && it.domain !== "general") pickedDoms.push(it.domain); return it; };

        const sfwOk = (it) => !isNsfwOpt(it);
        const tracks = [
            "action_tactical_gunfu",
            "action_wuxia_blade",
            "action_anime2real",
            "dance_kpop_mv",
            "dance_viral_street",
            "cinema_noir_thriller",
            "cinema_sunlit_romance",
            "intimate_boudoir",
            "intimate_wet_suite",
        ];
        const track = tracks[Math.floor(Math.random() * tracks.length)];
        for (const k of ALL_DIAL_KEYS) flavors[k] = "";
        flavors.dial_modes = {};
        flavors.pov = "off";
        flavors.talk_mode = "auto";
        flavors.sound_mode = "auto";
        flavors.fx_timing = "delayed_mid";

        if (track === "action_tactical_gunfu") {
            const cb = pickPref("combat", (x) => !isAnimeOpt(x) && !isWuxiaOpt(x) && !/action_/.test(x.id) && x.domain === "combat_action", (x) => x.domain === "combat_action");
            const pl = regDom(pickPref("place", (x) => x.domain === "combat_action" && !isWuxiaOpt(x) && !/colosseum|battlefield|dojo/.test(x.id) && sfwOk(x), (x) => x.domain === "combat_action" && sfwOk(x)));
            flavors.combat = cb?.id || "";
            flavors.place = pl?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain === "combat_action" && !isWuxiaOpt(x) && !isAnimeOpt(x) && sfwOk(x), (x) => domAllOk(x) && /tailored_black|street_cropped/.test(x.id)))?.id || "";
            flavors.style = pickPref("style", (x) => /john_wick|h3_astro|neo_noir|cyberpunk|denis/.test(x.id))?.id || "john_wick_neon_gunfu";
            flavors.camera = pickPref("camera", (x) => /cam_combat|multi_angle_action|whip_pan|track_side|low_angle_dutch|action_follow|top_down|staircase/.test(x.id))?.id || "multi_angle_action_close";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl) && !/ringlight|butterfly|boudoir/.test(x.id))?.id || "cyber_dual_gel";
            flavors.colour = pickPref("colour", (x) => /crimson|teal|emerald|kodak_vision3/.test(x.id))?.id || "crimson_john_wick_gold";
            flavors.fx = pickPref("fx", (x) => x.domain === "combat_action" && !isAnimeOpt(x))?.id || "";
            flavors.fx_timing = "from_start";
            flavors.music = pickPref("music", (x) => /john_wick|industrial|dark_cello|epic|drift_phonk/.test(x.id))?.id || "john_wick_club_techno_132";
            flavors.ambience = pickPref("ambience", (x) => x.domain === "combat_action" || /alley|tunnel|rain/.test(x.id))?.id || "combat_arena_reverb";
            flavors.motion = "max"; flavors.energy = "peak"; flavors.expression = "vivid"; flavors.expr_read = "intense"; flavors.life = "hyper"; flavors.talk_mode = "silent";
        } else if (track === "action_wuxia_blade") {
            const cb = pickPref("combat", (x) => isWuxiaOpt(x) && !isAnimeOpt(x), (x) => /sword|katana|spear|iaido/.test(itemBlob(x)));
            const pl = regDom(pickPref("place", (x) => x.domain === "combat_action" && /bamboo|dojo|lantern|shrine|courtyard|rainy/.test(x.id) && sfwOk(x), (x) => x.domain === "combat_action" && sfwOk(x)));
            flavors.combat = cb?.id || "";
            flavors.place = pl?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && /kimono|kunoichi|shihakusho/.test(x.id) && sfwOk(x), (x) => domAllOk(x) && x.domain === "combat_action" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /wuxia|h3_astro|style_ink_wash/.test(x.id))?.id || "wuxia_wirefu_cinema";
            flavors.camera = pickPref("camera", (x) => /cam_combat|orbit|arc_|whip_pan|multi_angle_action|track_side/.test(x.id))?.id || "cam_combat_kinetic_whip_zoom_ultimate";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl))?.id || "moonlight";
            flavors.colour = pickPref("colour", (x) => /emerald|crimson|kodak/.test(x.id))?.id || "emerald_anime_midnight";
            flavors.fx = pickPref("fx", (x) => /sword_spark|cherry_blossom|sakura|kinetic_shockwave/.test(x.id))?.id || "vfx_sword_spark_shower";
            flavors.fx_timing = "from_start";
            flavors.music = pickPref("music", (x) => /taiko|shamisen/.test(x.id))?.id || "taiko_war_drums_138";
            flavors.ambience = pickPref("ambience", (x) => /dojo|rain|alley|forest/.test(x.id))?.id || "dojo_wood_creak_wind";
            flavors.motion = "max"; flavors.energy = "peak"; flavors.expression = "stoic"; flavors.expr_read = "intense"; flavors.life = "hyper"; flavors.talk_mode = "silent";
        } else if (track === "action_anime2real") {
            const cb = pickPref("combat", (x) => isAnimeOpt(x) || isCyberOpt(x), (x) => x.domain === "combat_action");
            const pl = regDom(pickPref("place", (x) => x.domain === "combat_action" && /shibuya|crater|biolab|rooftop|marble_lobby|observation_deck|bamboo/.test(x.id) && sfwOk(x), (x) => x.domain === "combat_action" && sfwOk(x)));
            flavors.combat = cb?.id || "";
            flavors.place = pl?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && /anime2real|cyberpunk/.test(x.id) && sfwOk(x), (x) => domAllOk(x) && x.domain === "combat_action" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /anime2real|trigger_studio|cyberpunk_edgerunners|h3_sakuga/.test(x.id))?.id || "anime2real_live_action_vfx";
            flavors.camera = pickPref("camera", (x) => /sandevistan|cam_combat|orbit|multi_angle_action|whip_pan|crash_zoom/.test(x.id))?.id || "cam_combat_kinetic_whip_zoom_ultimate";
            flavors.light = pickPref("light", (x) => /anime2real|anime_cel|cyber_dual|lightning_storm/.test(x.id))?.id || "anime2real_elemental_aura_interactive_key";
            flavors.colour = pickPref("colour", (x) => /ufotable|emerald|teal_orange/.test(x.id))?.id || "ufotable_neon_hdr_contrast";
            flavors.fx = pickPref("fx", (x) => /anime2real|shockwave|crimson_lightning|plasma|sword_spark/.test(x.id))?.id || "vfx_kinetic_shockwave_dust_ring";
            flavors.fx_timing = "from_start";
            flavors.music = pickPref("music", (x) => /anime|sakuga|ufotable|cyberpunk_edgerunner|taiko/.test(x.id))?.id || "ufotable_orchestral_taiko_choir_140";
            flavors.ambience = "anime2real_elemental_hum_sparks";
            flavors.motion = "max"; flavors.energy = "peak"; flavors.expression = "vivid"; flavors.expr_read = "intense"; flavors.life = "hyper"; flavors.talk_mode = "silent";
        } else if (track === "dance_kpop_mv") {
            const ps = pickPref("pose", (x) => /kpop/.test(itemBlob(x)) && sfwOk(x), (x) => /dance_/.test(x.id) && sfwOk(x));
            const pl = regDom(pickPref("place", (x) => x.domain !== "combat_action" && /mirror_dance|proscenium_theater|hongdae|ballet_rehearsal|rotunda|elevat/.test(x.id) && sfwOk(x), (x) => x.domain === "general" && sfwOk(x)));
            flavors.pose = ps?.id || "";
            flavors.place = pl?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && /idol|kpop|coquette|balletcore|glam_backless|glam_sequined|cropped_jacket|tailored_black/.test(x.id) && sfwOk(x), (x) => domAllOk(x) && x.domain === "general" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /kpop_music_bank|korean_drama_glow|douyin_highgloss|japanese_4k_gravure/.test(x.id))?.id || "style_kpop_music_bank_4k_stage";
            flavors.camera = pickPref("camera", (x) => /cam_kpop|cam_viral|cam_beat_drop|cam_contour|cam_idol|cam_360|multi_angle_action|cam_palm/.test(x.id))?.id || "cam_kpop_inkigayo_ronin_hand_drop";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl) && /kpop|ring|editorial|soft_natural|cyber|neon|uv_blacklight/.test(x.id))?.id || "light_kpop_concert_multi_spot_haze";
            flavors.colour = pickPref("colour", (x) => /kpop|douyin|peach_milk|crimson|golden_hour/.test(x.id))?.id || "colour_kpop_pastel_milk_highlights";
            flavors.music = pickPref("music", (x) => /kpop|french_touch|club_house|jersey|city_pop/.test(x.id))?.id || "kpop_girl_crush_bass_drop_124";
            flavors.ambience = "amb_none_na";
            flavors.motion = "max"; flavors.energy = "peak"; flavors.expression = "vivid"; flavors.expr_read = "sly"; flavors.life = "hyper"; flavors.talk_mode = "silent";
        } else if (track === "dance_viral_street") {
            const ps = pickPref("pose", (x) => /(?:douyin|tiktok|viral|shuffle|bachata|house_jack|waacking|choochoo|sticky)/.test(itemBlob(x)) && sfwOk(x), (x) => /dance_/.test(x.id) && sfwOk(x));
            const isBeachPool = ps && /pool|beach|sticky|summer/.test(itemBlob(ps));
            const pl = regDom(pickPref("place", (x) => (isBeachPool ? /beach|pool|infinity|sunpad|promenade/.test(x.id) : /laundromat|bowling|parking|vinyl|mirror_dance/.test(x.id)) && x.domain !== "combat_action" && sfwOk(x), (x) => x.domain === "general" && sfwOk(x)));
            flavors.pose = ps?.id || "";
            flavors.place = pl?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && (isBeachPool || (pl && /beach|pool|infinity/.test(pl.id)) ? /swim_|bikini_swim|cutout_swimsuit/.test(x.id) : /street_|everyday_90s|everyday_oversized|coquette|y2k/.test(x.id)) && sfwOk(x), (x) => domAllOk(x) && x.domain === "general" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /douyin|y2k_digicam|90s_hi8|commercial_beauty|viral_2000s/.test(x.id))?.id || "style_douyin_highgloss_neon_beauty";
            flavors.camera = pickPref("camera", (x) => /cam_handheld_vertical|cam_beat_snap|cam_beat_drop|cam_palm|cam_360|cam_low_hero|cam_distant_wide|cam_viral/.test(x.id))?.id || "cam_beat_drop_punch_wide_combo";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl))?.id || (isBeachPool ? "sunset_silhouette_halo_rim" : "light_ring_beauty_plus_neon_rim");
            flavors.colour = pickPref("colour", (x) => (isBeachPool ? /golden_hour|portra|peach/.test(x.id) : /douyin|kpop|cinestill|kodak/.test(x.id)))?.id || "colour_kpop_pastel_milk_highlights";
            flavors.music = pickPref("music", (x) => /amapiano|reggaeton|baile|jersey|ukgarage|city_pop|afrobeats|house/.test(x.id))?.id || "city_pop_80s_112";
            flavors.ambience = "amb_none_na";
            flavors.motion = "max"; flavors.energy = "peak"; flavors.expression = "vivid"; flavors.expr_read = "sly"; flavors.life = "hyper"; flavors.talk_mode = "silent";
        } else if (track === "cinema_noir_thriller") {
            const pl = regDom(pickPref("place", (x) => x.domain !== "combat_action" && /cafe_rain|soho|diner|london_soho|executive_corner|loft_studio/.test(x.id) && sfwOk(x), (x) => x.domain === "general" && sfwOk(x)));
            flavors.place = pl?.id || "";
            flavors.pose = pickPref("pose", (x) => /^pose_/.test(x.id) && domAllOk(x) && sfwOk(x))?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && /tailored|trench|street_cropped|linen_blazer|turtleneck_midi/.test(x.id) && sfwOk(x), (x) => domAllOk(x) && x.domain === "general" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /h3_astro|wong_kar_wai|neo_noir|film_noir|genre_giallo/.test(x.id))?.id || "h3_astro_cinema";
            flavors.camera = pickPref("camera", (x) => camIsSafeCinema(x) && /table_two|ots_|shot_reverse|steadicam|push_in|dolly_push|mirror_reveal/.test(x.id))?.id || "dolly_push_to_ecu_eyes";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl))?.id || "neon_rain_window_caustics";
            flavors.colour = pickPref("colour", (x) => /kodak_vision3|cinestill|fuji_eterna|crimson/.test(x.id))?.id || "kodak_vision3_500t";
            flavors.talkstyle = pickPref("talkstyle", (x) => /earnest|husky|tactical|natural|banter/.test(x.id) && sfwOk(x))?.id || "earnest_dramatic_confession";
            flavors.music = pickPref("music", (x) => /piano_cello|dark_cello|sultry_jazz|jazz_lounge/.test(x.id))?.id || "piano_cello_65";
            flavors.ambience = pickPref("ambience", (x) => /cafe|rain|alley|subway|penthouse_night|room_tone/.test(x.id))?.id || "room_tone";
            flavors.motion = "slow"; flavors.energy = "calm"; flavors.expression = "natural"; flavors.expr_read = "tense"; flavors.life = "natural";
        } else if (track === "cinema_sunlit_romance") {
            const pl = regDom(pickPref("place", (x) => isDayPlace(x) && x.domain !== "combat_action" && x.domain !== "wet_pool" && sfwOk(x), (x) => x.domain === "general" && sfwOk(x)));
            flavors.place = pl?.id || "";
            flavors.pose = pickPref("pose", (x) => /^pose_/.test(x.id) && domAllOk(x) && sfwOk(x))?.id || "";
            flavors.wardrobe = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && /sundress|camisole|cardigan|linen_shirt|chiffon|sweater/.test(x.id) && sfwOk(x), (x) => domAllOk(x) && x.domain === "general" && sfwOk(x)))?.id || "";
            flavors.style = pickPref("style", (x) => /h3_astro|korean_drama|70s_16mm|french_new_wave/.test(x.id))?.id || "h3_astro_cinema";
            flavors.camera = pickPref("camera", (x) => camIsSafeCinema(x) && /push_in|arc_|steadicam|table_two|pullback_rise/.test(x.id))?.id || "push_in";
            flavors.light = pickPref("light", (x) => lightMatchesPlace(x, pl))?.id || "soft_natural_light";
            flavors.colour = pickPref("colour", (x) => /portra|golden_hour|fuji_eterna|champagne/.test(x.id))?.id || "colour_kodak_portra_400_warm";
            flavors.talkstyle = pickPref("talkstyle", (x) => /warm_witty|bright_vlog|natural_conversational/.test(x.id) && sfwOk(x))?.id || "warm_witty_banter";
            flavors.music = pickPref("music", (x) => /bossa_nova|city_pop|shoegaze|piano_cello/.test(x.id))?.id || "bossa_nova_sunset_88";
            flavors.ambience = pickPref("ambience", (x) => /cafe|ocean_cliff|waves|room_tone/.test(x.id))?.id || "room_tone";
            flavors.motion = "slow"; flavors.energy = "calm"; flavors.expression = "natural"; flavors.expr_read = "warm"; flavors.life = "alive";
        } else if (track === "intimate_boudoir") {
            const pl = regDom(pickPref("place", (x) => ["bedroom", "sofa_lounge", "mirror_vanity", "bdsm_dom"].includes(x.domain)));
            const domP = pl?.domain || "bedroom";
            const wr = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && (isNsfwOpt(x) || /lingerie|glam|silk|partial|nude/.test(x.id)), (x) => domAllOk(x) && x.domain !== "combat_action"));
            const ex = regDom(pickPref("explicit", (x) => domAllOk(x)));
            const pb = regDom(pickPref("fetish", (x) => domAllOk(x)));
            flavors.place = pl?.id || "";
            flavors.wardrobe = wr?.id || "";
            flavors.explicit = ex?.id || "";
            flavors.fetish = pb?.id || "";
            const exIdB = String(ex?.id || "");
            const isContB = exIdB.startsWith("cont_") || exIdB === "stage_aftercare_cooldown_whisper" || exIdB === "stage_slow_grind_lap_tease_insertion";
            const isTwoCutB = /_2cut_|_to_(?:rear|press|carry|missionary|sunbed|double_tease)$/.test(exIdB) && !/_3cut_/.test(exIdB);
            const camCompatB = (x) => {
                if (!camIsSafeIntimate(x) || !domainsMatch(domP, x.domain)) return false;
                if (isContB && /(?:multi_position_3cut|multi_angle|shot_reverse|whip_pan|match_cut|graphic_match|smash_cut|coverage_match)/.test(x.id)) return false;
                if (isTwoCutB && /multi_position_3cut|multi_angle_action|multi_angle_orbit/.test(x.id)) return false;
                if (exIdB && !/(?:^solo_|^undress_)/.test(exIdB) && /(?:elevator_3stop|body_contour_s_curve)/.test(x.id)) return false;
                return true;
            };
            flavors.style = pickPref("style", (x) => /glamour_boudoir|erotic_thriller|h3_astro|japanese_4k_gravure/.test(x.id))?.id || "glamour_boudoir_8k";
            flavors.camera = pickPref("camera", (x) => camCompatB(x) && /multi_position_3cut|portrait_vertical|mirror_|push_in|low_angle_power|dolly_push|coverage_match/.test(x.id), camCompatB)?.id || "push_in";
            flavors.light = pickPref("light", (x) => domainsMatch(domP, x.domain) && lightMatchesPlace(x, pl) && /candlelight|vip_amber|red_velvet|fireplace|soft_natural|sunset_blinds|tokyo_love/.test(x.id))?.id || "candlelight_flicker_boudoir";
            flavors.colour = pickPref("colour", (x) => /champagne|peach_milk|crimson|kodak/.test(x.id))?.id || "champagne_honey_glow";
            flavors.ambience = pickPref("ambience", (x) => domainsMatch(domP, x.domain) && /intimate_skin|silk_sheets|fireplace|love_hotel|penthouse/.test(x.id))?.id || "intimate_skin_foley";
            flavors.motion = "natural"; flavors.energy = "steady"; flavors.expression = "vivid"; flavors.expr_read = "sensual"; flavors.life = "alive";
        } else {
            const pl = regDom(pickPref("place", (x) => ["wet_shower", "wet_tub", "wet_pool", "car_cabin", "office_desk"].includes(x.domain)));
            const domP = pl?.domain || "wet_shower";
            const wr = regDom(pickPref("wardrobe", (x) => domAllOk(x) && x.domain !== "combat_action" && (domP.startsWith("wet_") ? /nude_wet|swim_|bikini|nude_oiled|nude_full/.test(x.id) : /partial_|office_siren|glam_|tailored/.test(x.id)), (x) => domAllOk(x) && x.domain !== "combat_action"));
            const ex = regDom(pickPref("explicit", (x) => domAllOk(x) && x.domain === domP, (x) => domAllOk(x)));
            const pb = regDom(pickPref("fetish", (x) => domAllOk(x)));
            flavors.place = pl?.id || "";
            flavors.wardrobe = wr?.id || "";
            flavors.explicit = ex?.id || "";
            flavors.fetish = pb?.id || "";
            const exIdW = String(ex?.id || "");
            const isContW = exIdW.startsWith("cont_");
            const isTwoCutW = /_2cut_|_to_(?:rear|press|carry|missionary|sunbed|double_tease)$/.test(exIdW) && !/_3cut_/.test(exIdW);
            const camCompatW = (x) => {
                if (!camIsSafeIntimate(x) || !domainsMatch(domP, x.domain)) return false;
                if (isContW && /(?:multi_position_3cut|multi_angle|shot_reverse|whip_pan|match_cut|graphic_match|smash_cut|coverage_match)/.test(x.id)) return false;
                if (isTwoCutW && /multi_position_3cut|multi_angle_action|multi_angle_orbit/.test(x.id)) return false;
                if (exIdW && !/(?:^solo_|^undress_)/.test(exIdW) && /(?:elevator_3stop|body_contour_s_curve)/.test(x.id)) return false;
                return true;
            };
            flavors.style = pickPref("style", (x) => /glamour_boudoir|erotic_thriller|h3_astro/.test(x.id))?.id || "glamour_boudoir_8k";
            flavors.camera = pickPref("camera", (x) => camCompatW(x) && /multi_position_3cut|portrait_vertical|push_in|buckle_up|low_angle_power|coverage_match/.test(x.id), camCompatW)?.id || "push_in";
            flavors.light = pickPref("light", (x) => domainsMatch(domP, x.domain) && lightMatchesPlace(x, pl))?.id || (domP === "wet_pool" ? "sunset_silhouette_halo_rim" : "soft_natural_window");
            flavors.colour = pickPref("colour", (x) => /champagne|kodak|golden_hour/.test(x.id))?.id || "champagne_honey_glow";
            flavors.ambience = pickPref("ambience", (x) => domainsMatch(domP, x.domain))?.id || (domP === "wet_shower" ? "bathhouse_steam_water_drip" : "intimate_skin_foley");
            flavors.motion = "natural"; flavors.energy = "steady"; flavors.expression = "vivid"; flavors.expr_read = "sensual"; flavors.life = "alive";
        }
        normalizePerfFlavors(flavors);
        persistFlavors();
        syncAllWidgets();
        say(`Surprise Roll (${track}, ${nSubj} subj, ${aspSpec.label}, locked ✓).`, "hint");
    }

    function runMatchDials() {
        const txt = String(briefEl.value || "").toLowerCase();
        if (!txt.trim()) return say("Type a brief first so Match Dials can score matching dials.", "hint");
        pushUndoSnapshot();
        const tokens = txt.split(/[^a-z0-9]+/).filter((t) => t.length >= 4);
        const asp = parseAspectSpec(getAspect()).bucket;
        const refPlanObj = readRefPlanObj();
        const wiredSubjs = new Set((refPlanObj.refs || []).map((r) => Number(r.subject || 0)).filter((n) => n > 0));
        const nSubj = Math.max(1, wiredSubjs.size || Object.keys(refPlanObj.subjects || {}).length || 1);
        const pickedDoms = [];
        const matchOrder = ["place", "explicit", "combat", "pose", "wardrobe", "fetish", "camera", "style", "light", "colour", "lens", "fx", "character", "era", "tv_show", "talkstyle", "accent", "ambience", "music"];
        let matched = 0;
        for (const k of matchOrder) {
            const items = dialControllers[k]?.getItems() || [];
            let best = null;
            let bestScore = 0;
            for (const it of items) {
                if (it.multi_hop_only) continue;
                if (asp !== "either" && it.aspect_best !== "either" && it.aspect_best !== asp) continue;
                if (it.domain && it.domain !== "general" && !pickedDoms.every((d) => domainsMatch(d, it.domain))) continue;
                const blob = `${it.id || ""} ${it.label || ""} ${it.group || ""}`.toLowerCase();
                if (nSubj <= 1 && (Number(it.people || 0) >= 2 || /duet|two_shot|ensemble|s1_s9/.test(blob))) continue;
                if (nSubj >= 2 && (Number(it.people || 0) === 1 || /\bsolo\b/.test(blob))) continue;
                const hay = `${it.label} ${it.id} ${it.group}`.toLowerCase();
                let sc = 0;
                for (const tk of tokens) if (hay.includes(tk)) sc += 1;
                if (sc > bestScore) { bestScore = sc; best = it; }
            }
            if (best && bestScore >= 1) {
                flavors[k] = best.id;
                if (best.domain && best.domain !== "general") pickedDoms.push(best.domain);
                matched += 1;
            }
        }
        persistFlavors();
        syncAllWidgets();
        say(`Matched ${matched} domain-safe dial(s) from your brief.`, "hint");
    }

    function runComposeBrief() {
        const cleanLbl = (s) => String(s || "")
            .replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF]+/gu, "")
            .replace(/^(?:NUDE(?:\s*\(.*?\))?|FETISH(?:\s+NUDE)?|PARTIAL|TOPLESS|BOTTOMLESS|SFW|NSFW|UBER FIGHT(?:\s*\(ms\))?)\s*[—\-–:]+\s*/i, "")
            .replace(/\s{2,}/g, " ")
            .trim();
        const doc = readRefPlanObj();
        const castNames = doc.refs.filter((r) => r.subject).map((r) => doc.subjects?.[r.subject]?.name || `@${r.tag}`);
        const who = castNames.length ? castNames.join(" and ") : "The lead character";
        const pName = cleanLbl(dialControllers.place?.getItem(parseMultiValue(flavors.place)[0])?.label?.split("·")[0] || "");
        const wItems = parseMultiValue(flavors.wardrobe).map((id) => cleanLbl(dialControllers.wardrobe?.getItem(id)?.label || "")).filter(Boolean);
        const wName = wItems.join(" and ");
        const act = cleanLbl(
            dialControllers.combat?.getItem(parseMultiValue(flavors.combat)[0])?.label
            || dialControllers.explicit?.getItem(parseMultiValue(flavors.explicit)[0])?.label
            || dialControllers.pose?.getItem(parseMultiValue(flavors.pose)[0])?.label
            || "moves expressively with natural eye contact"
        );
        const bits = [who];
        if (wName) bits.push(`wearing ${wName.toLowerCase()}`);
        if (pName) bits.push(`inside ${pName.toLowerCase()}`);
        bits.push(`— ${act}.`);
        pushUndoSnapshot();
        briefEl.value = bits.join(" ");
        saveDraft();
    }

    function resetAllDials() {
        pushUndoSnapshot();
        for (const k of ALL_DIAL_KEYS) flavors[k] = "";
        flavors.dial_modes = {};
        persistFlavors();
        syncAllWidgets();
    }

    function renderActiveStrip() {
        activeStrip.textContent = "";
        const aspSpec = parseAspectSpec(getAspect());
        const targetLabel = aspSpec.label;
        const targetBucket = aspSpec.bucket;
        let has916 = false;
        let has169 = false;
        const activeEntries = [];
        for (const k of ALL_DIAL_KEYS) {
            for (const id of parseMultiValue(flavors[k])) {
                const it = dialControllers[k]?.getItem(id);
                if (!it) continue;
                activeEntries.push([k, id, it]);
                if (it.aspect_best === "9:16") has916 = true;
                if (it.aspect_best === "16:9") has169 = true;
            }
        }
        activeCountPill.textContent = `${activeEntries.length} active`;

        // Aspect mix pill
        const hasMix = (has916 && has169) || (targetBucket === "9:16" && has169) || (targetBucket === "16:9" && has916);
        const aspBtn = button(
            hasMix ? `⚠️ Aspect Mix (${targetLabel}) — Fix` : `${targetLabel} Match ✓`,
            hasMix ? `Clear dials locked against ${targetLabel}` : `All active dials match ${targetLabel} canvas aspect`,
            () => {
                if (!hasMix) return;
                pushUndoSnapshot();
                for (const k of ALL_DIAL_KEYS) {
                    const kept = parseMultiValue(flavors[k]).filter((id) => {
                        const it = dialControllers[k]?.getItem(id);
                        return !it || it.aspect_best === "either" || targetBucket === "either" || it.aspect_best === targetBucket;
                    });
                    flavors[k] = serializeMultiValue(kept);
                }
                persistFlavors();
                syncAllWidgets();
            },
            hasMix ? "h3st-pill h3st-pill-warn" : "h3st-pill h3st-pill-ok",
        );
        activeStrip.appendChild(aspBtn);

        // Domain conflict check
        const domItems = [];
        for (const k of ["place", "wardrobe", "explicit", "fetish"]) {
            for (const id of parseMultiValue(flavors[k])) {
                const it = dialControllers[k]?.getItem(id);
                if (it && it.domain && it.domain !== "general") domItems.push({ k, it });
            }
        }
        let domClash = null;
        for (let i = 0; i < domItems.length; i++) {
            for (let j = i + 1; j < domItems.length; j++) {
                if (!domainsMatch(domItems[i].it.domain, domItems[j].it.domain)) {
                    domClash = `${domItems[i].it.domain} vs ${domItems[j].it.domain}`;
                    break;
                }
            }
            if (domClash) break;
        }
        if (domClash) {
            const dBtn = button(`⚠️ Domain Clash (${domClash}) — Clear Mismatch`, "Keep Place domain & clear clashing wardrobe/staging dials", () => {
                pushUndoSnapshot();
                const anchorDom = domItems[0].it.domain;
                for (const k of ["wardrobe", "explicit", "fetish"]) {
                    const kept = parseMultiValue(flavors[k]).filter((id) => {
                        const it = dialControllers[k]?.getItem(id);
                        return !it || domainsMatch(anchorDom, it.domain);
                    });
                    flavors[k] = serializeMultiValue(kept);
                }
                persistFlavors();
                syncAllWidgets();
            }, "h3st-pill h3st-pill-warn");
            activeStrip.appendChild(dBtn);
        }

        // Best Duration advisory + H3 5+17k frame grid readout
        const durSec = parseFloat(String(getDurationLabel() || "10").replace(/[^\d.]/g, "")) || 10;
        const _h3RawN = Math.max(5, Math.round(durSec * 24));
        const h3Frames = _h3RawN + (5 - (_h3RawN % 17)) % 17;
        const h3SnapSec = (h3Frames / 24).toFixed(2);
        const gridPill = el("span", "h3st-pill", `🎞 ${durSec}s → ${h3Frames}f (${h3SnapSec}s)`);
        gridPill.title = `MiniMax H3 native 24 fps 5+17k latent grid: ${durSec}s snaps up to ${h3Frames} frames (${h3SnapSec}s).`;
        activeStrip.appendChild(gridPill);
        const needLong = activeEntries.find(([_k, _id, it]) => it.duration_best && parseFloat(it.duration_best) > durSec + 0.4);
        if (needLong) {
            const bestPill = el("span", "h3st-pill h3st-pill-warn", `⏱ Best Length: ${needLong[2].duration_best} (current ${durSec}s)`);
            bestPill.title = needLong[2].duration_tip || "Recommended duration for unhurried pacing";
            activeStrip.appendChild(bestPill);
        }

        for (const [k, id, it] of activeEntries) {
            const chip = button(`${it.label} ×`, `Remove ${it.label}`, () => {
                pushUndoSnapshot();
                const next = parseMultiValue(flavors[k]).filter((x) => x !== id);
                dialControllers[k]?.setValue(serializeMultiValue(next));
                renderActiveStrip();
            }, "h3e-btn h3st-chip-on");
            chip.style.padding = "2px 6px";
            chip.style.fontSize = "10.5px";
            activeStrip.appendChild(chip);
        }
        updateTrayButton();
    }

    function syncAllWidgets() {
        swTime.chk.checked = Boolean(flavors.time_tied);
        swKinetic.chk.checked = Boolean(flavors.kinetic_grip);
        swEye.chk.checked = Boolean(flavors.eye_scan);
        swDouble.chk.checked = Boolean(flavors.double_knot);
        swWake.chk.checked = Boolean(flavors.wake_writer);
        linkPrevChk.checked = Boolean(flavors.link_prev_hop);
        fxTimingSel.value = flavors.fx_timing || "delayed_mid";
        syncPerfCards();
        syncChips();
        for (const k of ALL_DIAL_KEYS) dialControllers[k]?.setValue(flavors[k] || "");
        renderActiveStrip();
        renderReferenceBible();
    }

    // 10. Server Status & API Calls
    function paintServerButtons() {
        if (_sharedStatus.backend) writerModeSel.value = _sharedStatus.backend;
        if (_sharedStatus.running) {
            statusPill.textContent = `${_sharedStatus.backend_label || "Writer"} Ready`;
            statusPill.className = "h3st-pill h3st-pill-ok";
        } else if (_sharedStatus.loading) {
            statusPill.textContent = `${_sharedStatus.backend_label || "Writer"} Loading…`;
            statusPill.className = "h3st-pill";
        } else {
            statusPill.textContent = `${_sharedStatus.backend_label || "Writer"} Offline`;
            statusPill.className = "h3st-pill";
        }
    }

    let statusRefreshSeq = 0;
    async function refreshStatus(forceCatalog = false) {
        const mySeq = ++statusRefreshSeq;
        try {
            const needCat = forceCatalog || !_sharedCatalog;
            const url = needCat ? SANDTIE_OPTIONS_URL : `${SANDTIE_OPTIONS_URL}?lite=1`;
            const r = await fetch(url);
            const j = await r.json();
            if (mySeq !== statusRefreshSeq) return;
            if (j.ok) {
                _sharedStatus = {
                    running: Boolean(j.running),
                    loading: Boolean(j.loading),
                    backend: j.backend,
                    backend_label: j.backend_label,
                    model: j.model,
                    startup_error: j.startup_error || "",
                };
                paintServerButtons();
                if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
                if (Array.isArray(j.video_files)) {
                    refBankVideoFiles = j.video_files;
                    fillVideoSelect(vidInput.value.trim());
                }
                if (j.catalog) {
                    _sharedCatalog = j.catalog;
                    populateFromCatalog(_sharedCatalog);
                }
            }
        } catch (_) {}
    }

    function populateFromCatalog(cat) {
        if (!cat) return;
        for (const k of ALL_DIAL_KEYS) {
            const items = cat[k] || [];
            dialControllers[k]?.populate(items);
        }
        scriptSel.textContent = "";
        const ph = el("option", null, `— Pick from ${(cat.scripts || []).length} clean SandTie scripts —`);
        ph.value = "";
        scriptSel.appendChild(ph);
        const grpMap = new Map();
        for (const sc of cat.scripts || []) {
            const g = sc.group || "Showcase";
            if (!grpMap.has(g)) grpMap.set(g, []);
            grpMap.get(g).push(sc);
        }
        for (const [g, list] of grpMap.entries()) {
            const og = document.createElement("optgroup");
            og.label = g;
            for (const sc of list) {
                const o = el("option", null, sc.label);
                o.value = sc.id;
                og.appendChild(o);
            }
            scriptSel.appendChild(og);
        }
        refBankItems = cat.ref_bank || [];
        syncAllWidgets();
    }

    let writerLoadSeq = 0;
    let writerCfgLoaded = false;
    async function loadWriterSettings() {
        const mySeq = ++writerLoadSeq;
        try {
            const r = await fetch(LLM_URL);
            const j = await r.json();
            if (!j.ok || mySeq !== writerLoadSeq) return;
            writerCfgLoaded = true;
            cfgBackSel.textContent = "";
            const backs = Array.isArray(j.backends) && j.backends.length
                ? j.backends
                : [{ id: "lmstudio", label: "Local server" }, { id: "ninfer", label: "nInfer" }];
            for (const b of backs) {
                const o = el("option", null, b.label || b.id);
                o.value = b.id;
                cfgBackSel.appendChild(o);
            }
            cfgBackSel.value = j.backend || "lmstudio";
            writerModeSel.value = j.backend || "lmstudio";
            cfgUrlInp.value = j.server_url || "";
            cfgModelInp.value = j.model || "";
            cfgModelInp.placeholder = cfgBackSel.value === "ninfer"
                ? "model id (auto after Start; blank = auto)"
                : "model id (optional if your server has one loaded)";
            cfgUnloadChk.checked = j.unload_on_run !== false;
            const curPaths = (j.server_paths && j.server_paths[cfgBackSel.value]) || {};
            const hasProg = (backs.find((b) => b.id === cfgBackSel.value)?.program) || (cfgBackSel.value === "ninfer");
            cfgPathRow.hidden = !hasProg;
            cfgExeInp.value = curPaths.exe || "";
            cfgExeInp.placeholder = curPaths.found_exe
                ? `Auto-detected: ${curPaths.found_exe}`
                : "nInfer exe path (e.g. C:\\ninfer\\ninfer-serve.exe)";
            cfgModelFileInp.value = curPaths.model_file || "";
            const ctxVal = String(curPaths.ctx_size || j.ctx_size || 65536);
            if (!Array.from(cfgCtxSel.options || cfgCtxSel.children || []).some((o) => o.value === ctxVal)) {
                const co = el("option", null, `${ctxVal} ctx (custom)`);
                co.value = ctxVal;
                cfgCtxSel.appendChild(co);
            }
            cfgCtxSel.value = ctxVal;
            cfgModelPick.textContent = "";
            const ph = el("option", null, (j.models || []).length ? "— Pick loaded model —" : "— No models listed —");
            ph.value = "";
            cfgModelPick.appendChild(ph);
            for (const m of j.models || []) {
                const mid = typeof m === "string" ? m : (m?.id || "");
                if (!mid) continue;
                const o = el("option", null, (m?.loaded ? "● " : "") + mid);
                o.value = mid;
                cfgModelPick.appendChild(o);
            }
        } catch (_) {}
    }

    async function saveWriterSettings({ quiet = false } = {}) {
        try {
            const activeBack = cfgBackSel.value || writerModeSel.value || "lmstudio";
            const patch = {
                backend: activeBack,
                server_url: cfgUrlInp.value.trim(),
                model: cfgModelInp.value.trim(),
                unload_on_run: cfgUnloadChk.checked,
            };
            if (activeBack === "ninfer" || !cfgPathRow.hidden) {
                const ctxNum = Number(cfgCtxSel.value) || 65536;
                patch.ctx_size = ctxNum;
                patch.servers = {
                    [activeBack]: {
                        exe: cfgExeInp.value.trim(),
                        model_file: cfgModelFileInp.value.trim(),
                        ctx_size: ctxNum,
                    },
                };
            }
            const r = await fetch(LLM_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify(patch),
            });
            const j = await r.json();
            if (!j.ok) {
                say(j.error || "Failed to save writer settings.", "error");
                return false;
            }
            await Promise.all([loadWriterSettings(), refreshStatus(false)]);
            if (!quiet) {
                say(`Saved writer (${j.backend || activeBack} @ ${j.server_url || cfgUrlInp.value}).`, "hint");
            }
            return true;
        } catch (err) {
            say(String(err), "error");
            return false;
        }
    }

    async function toggleServer(action) {
        const btn = action === "start" ? startBtn : stopBtn;
        btn.disabled = true;
        try {
            if (action === "start" && writerCfgLoaded) {
                const savedOk = await saveWriterSettings({ quiet: true });
                if (!savedOk) return;
            }
            say(action === "start" ? "Starting local writer…" : "Stopping local writer…", "hint");
            const reqBody = { action };
            if (action === "start" && writerCfgLoaded) {
                if (cfgModelFileInp.value.trim()) reqBody.model_file = cfgModelFileInp.value.trim();
                if (cfgCtxSel.value) reqBody.ctx_size = Number(cfgCtxSel.value);
            }
            const r = await fetch(LLM_URL, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqBody),
            });
            const j = await r.json();
            if (!j.ok) {
                await refreshStatus(false);
                say(j.error || j.note || `Failed to ${action} local writer.`, "error");
                return;
            }
            if (action === "stop") {
                await refreshStatus(false);
                say(j.note || "Stopped local writer.", "hint");
                return;
            }
            if (j.running) {
                await refreshStatus(false);
                if (writerCfgLoaded) await loadWriterSettings();
                say(`${_sharedStatus.backend_label || "Writer"} Ready!`, "hint");
                return;
            }
            say(j.note || "Starting local writer… waiting for server.", "hint");
            for (let i = 0; i < 80; i++) {
                await new Promise((res) => setTimeout(res, 1500));
                await refreshStatus(false);
                if (_sharedStatus.running) {
                    if (writerCfgLoaded) await loadWriterSettings();
                    say(`${_sharedStatus.backend_label || "Writer"} Ready!`, "hint");
                    return;
                }
                if (_sharedStatus.startup_error && !_sharedStatus.loading) {
                    say(`Writer stopped during startup: ${_sharedStatus.startup_error}`, "error");
                    return;
                }
            }
            say("Timed out waiting for local writer — check server.err in your nInfer folder.", "error");
        } catch (err) {
            say(String(err), "error");
        } finally {
            btn.disabled = false;
        }
    }

    function syncBlockToSimplePrompt(txt) {
        const clean = String(txt || "").trim();
        if (standalone || !clean) return "";
        const swRaw = String(widgetByName(node, "swap_script")?.value || "").trim();
        const spRaw = String(widgetByName(node, "shot_plan")?.value || "").trim();
        let hasShots = false;
        if (spRaw) {
            try {
                const spParsed = JSON.parse(spRaw);
                const arr = Array.isArray(spParsed) ? spParsed : spParsed?.shots;
                hasShots = Array.isArray(arr) && arr.length > 0;
            } catch {
                hasShots = true;
            }
        }
        if (swRaw) {
            return "\n• SWAP script is active — click Accept to clear Swap and queue Standard (Simple).";
        }
        if (hasShots) {
            return "\n• Shots are active on SCRIPT — click Accept to switch to Standard (Simple), or → Script Hop.";
        }
        if (node?.properties?.h3_editor_mode === "shots") {
            return "\n• SCRIPT is in Shots mode with 0 shots — click Accept (Standard) or → Script Hop.";
        }
        const pw = widgetByName(node, "prompt");
        if (pw) {
            pw.value = clean;
            try { pw.callback?.(pw.value, node.graph?.canvas, node); } catch (_) {}
            try { node._h3R2?.script?.refresh?.(); } catch (_) {}
            node.graph?.setDirtyCanvas?.(true, true);
            const chN = Math.max(1, parseInt(widgetByName(node, "chains")?.value, 10) || 1);
            return chN > 1
                ? `\n• Synced to prompt, but chains=${chN} on RUN will run ${chN} clips — click Accept to set chains = 1.`
                : " (synced to Simple prompt — ready to Queue)";
        }
        return "";
    }

    async function loadOrAdaptScript(adapt) {
        const pid = scriptSel.value;
        if (!pid) return say("Select a script first.", "hint");
        const r = await fetch(SANDTIE_PRESET_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id: pid, adapt: Boolean(adapt), duration: getDurationLabel(),
                ref_plan: getRefPlan(), voice_files: getVoiceFiles(),
                flavors, brief: briefEl.value,
            }),
        });
        const j = await r.json();
        if (!j.ok) return say(j.error || "Failed to load script", "error");
        pushUndoSnapshot();
        if (j.script) blockBox.value = j.script;
        if (j.plan) planBox.value = j.plan;
        if (j.brief && !briefEl.value.trim()) briefEl.value = j.brief;
        if (j.updated_ref_plan) setRefPlan(j.updated_ref_plan);
        saveDraft();
        updateTelemetry();
        const extraNote = j.script ? syncBlockToSimplePrompt(j.script) : "";
        say((adapt ? `Adapted script to wired refs & dials (${j.mode}).` : "Loaded raw script.") + extraNote, "hint");
    }

    async function runVideoExtractor() {
        const vf = vidInput.value.trim();
        if (!vf) return say("Enter a reference video filename inside input/ or h3_refs/.", "error");
        say(`Extracting choreography & camera beats from ${vf}…`, "hint");
        const r = await fetch(SANDTIE_EXTRACT_URL, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_file: vf,
                in_sec: parseFloat(inSecInp.value || "0") || 0,
                out_sec: parseFloat(outSecInp.value || "0") || 0,
                auto_wake: Boolean(flavors.wake_writer),
            }),
        });
        const j = await r.json();
        if (!j.ok) return say(j.error || "Video extractor failed", "error");
        j._video_file = vf;
        extractedVideoData = j;
        const madeTag = j.made_of ? ` · ${j.made_of}` : "";
        extractedBadge.textContent = `${j.duration_s}s · ${(j.beats || []).length} beats${madeTag}`;
        extractedBadge.className = "h3st-pill h3st-pill-ok";
        if (j.shot1 || (j.beats || []).length) {
            pushUndoSnapshot();
            const s1Clean = String(j.shot1 || "").replace(/^(?:the\s+)?\[\s*shot\s+1\s*\][,:\s-]*/i, "").trim();
            planBox.value = [s1Clean ? `[Shot 1] ${s1Clean}` : "", ...(j.beats || [])].filter(Boolean).join("\n");
            saveDraft();
        }
        say(`Extracted ${(j.beats || []).length} timed beats (${j.made_of || "live_action"}) from ${vf}.`, "hint");
    }

    async function runSandTie(stage) {
        if (isBusy()) return;
        const aspSpec = parseAspectSpec(getAspect());
        flavors.aspect = aspSpec.label || aspSpec.bucket || "16:9";
        if (standalone) {
            flavors.output_format = h3FormatCodeFromLabel(widgetByName(node, "h3_format")?.value || "");
        }
        flavors.current_block = blockBox.value;
        setBusyState(true);
        abortBtn.hidden = false;
        activeAbortCtrl = new AbortController();
        const wakingLocal = (stage !== "skeleton" && stage !== "cpu") && !_sharedStatus.running && swWake.chk.checked && (_sharedStatus.backend === "ninfer" || writerModeSel.value === "ninfer");
        say(
            stage === "skeleton"
                ? "Building 0-VRAM beat skeleton…"
                : (stage === "cpu"
                    ? "Assembling instant CPU H3 prompt…"
                    : (wakingLocal ? `Waking nInfer & running SandTie (${stage})…` : `Running SandTie (${stage})…`)),
            "hint",
        );
        try {
            const r = await fetch(SANDTIE_WRITE_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                signal: activeAbortCtrl.signal,
                body: JSON.stringify({
                    stage,
                    brief: briefEl.value,
                    plan: stage === "fast" ? "" : planBox.value,
                    duration: getDurationLabel(),
                    ref_plan: getRefPlan(),
                    start_image_file: getStartImage(),
                    voice_files: getVoiceFiles(),
                    prev_hop_context: previousHopContext ? previousHopContext() : "",
                    flavors,
                    extracted_video: extractedVideoData,
                }),
            });
            const j = await r.json();
            if (!j.ok && stage !== "fast" && stage !== "write") {
                return say(j.error || (j.errors || []).join("; ") || "SandTie failed", "error");
            }
            pushUndoSnapshot();
            if (j.skeleton && (stage === "skeleton" || !planBox.value.trim())) planBox.value = j.skeleton;
            if (j.plan && (stage === "plan" || stage === "fast" || stage === "write" || stage === "cpu")) planBox.value = j.plan;
            if (j.block) blockBox.value = j.block;
            if (j.updated_ref_plan) setRefPlan(j.updated_ref_plan);
            saveDraft();
            updateTelemetry();
            const warns = (j.warnings || []).map((w) => `• ${w}`).join("\n");
            if (!j.ok) {
                say(((j.errors || []).join("; ") || j.error || "Contract issue") + (warns ? "\n" + warns : ""), "error");
            } else {
                let extraNote = "";
                if (!standalone && j.block && (stage === "fast" || stage === "write" || stage === "cpu" || stage === "dialogue")) {
                    extraNote = syncBlockToSimplePrompt(j.block);
                }
                say(`${stage.toUpperCase()} ready (${j.mode || "H3"}).${extraNote}` + (warns ? `\n${warns}` : ""), "hint");
            }
        } catch (err) {
            if (err?.name !== "AbortError") say(String(err), "error");
        } finally {
            activeAbortCtrl = null;
            abortBtn.hidden = true;
            setBusyState(false);
        }
    }

    shell.addEventListener("click", () => closeAllPopovers(null));
    document.addEventListener("click", () => closeAllPopovers(null));

    // Assemble layout inside mountBody cleanly
    const actionBar = el("div", "h3st-row");
    actionBar.append(fastBtn, skelBtn);
    if (standalone) {
        actionBar.appendChild(cpuBtn);
        if (legacyButtons?.planBtn) actionBar.appendChild(legacyButtons.planBtn);
        if (legacyButtons?.writeBtn) actionBar.appendChild(legacyButtons.writeBtn);
        const applyBtn = button("✓ Apply to Node Outputs", "Sync prompt, storyboard, soundscape, music & ref_plan onto node sockets", () => onApplyStandalone?.(), "h3e-btn h3e-btn-accent");
        actionBar.appendChild(applyBtn);
    } else {
        if (legacyButtons?.planBtn) actionBar.appendChild(legacyButtons.planBtn);
        if (legacyButtons?.writeBtn) actionBar.appendChild(legacyButtons.writeBtn);
        if (legacyButtons?.acceptBtn) actionBar.appendChild(legacyButtons.acceptBtn);
        if (legacyButtons?.hopTargetSel) actionBar.appendChild(legacyButtons.hopTargetSel);
        if (legacyButtons?.sendHopBtn) actionBar.appendChild(legacyButtons.sendHopBtn);
    }
    const barSpacer = el("span");
    barSpacer.style.flex = "1 1 auto";
    actionBar.append(barSpacer, abortBtn);

    const planTools = el("div", "h3st-row");
    const planToolsSpacer = el("span");
    planToolsSpacer.style.flex = "1 1 auto";
    planTools.append(planToolsSpacer, clearPlanBtn);

    const blockTools = el("div", "h3st-row");
    blockTools.append(telemetryPill, freshDlgBtn, copyBtn, clearBlockBtn, clearBothBtn, undoBtn);

    shell.append(headRow, swRow, writerCfgDrawer, activeStrip, primaryGrid, toolRow, secondaryDrawer, perfBox, scriptsDrawer, clipDrawer, bibleBox);

    if (legacyButtons?.beforeEl && legacyButtons.beforeEl.parentElement === mountBody) {
        mountBody.insertBefore(shell, legacyButtons.beforeEl);
    } else {
        mountBody.appendChild(shell);
    }
    if (legacyButtons?.row && legacyButtons.row.parentElement === mountBody) {
        legacyButtons.row.textContent = "";
        legacyButtons.row.appendChild(actionBar);
    } else {
        mountBody.appendChild(actionBar);
    }
    if (legacyButtons?.planCol) {
        legacyButtons.planCol.insertBefore(planTools, planBox);
    }
    if (legacyButtons?.blockCol) {
        legacyButtons.blockCol.insertBefore(blockTools, blockBox);
    } else {
        mountBody.appendChild(blockTools);
    }

    refreshComboSelect();
    if (_sharedCatalog) populateFromCatalog(_sharedCatalog);
    refreshStatus(!_sharedCatalog);
    if (typeof window !== "undefined") {
        window.addEventListener?.("htc:refmods-changed", () => {
            fetch(SANDTIE_REFBANK_URL)
                .then((r) => (r.ok ? r.json() : null))
                .then((j) => {
                    if (j?.ok && Array.isArray(j.items)) {
                        refBankItems = j.items;
                        if (Array.isArray(j.audio_files)) refBankAudioFiles = j.audio_files;
                        if (_sharedCatalog) _sharedCatalog.ref_bank = refBankItems;
                        renderReferenceBible();
                    }
                })
                .catch(() => {});
        });
    }

    return {
        fastBtn,
        refreshStatus,
        runSandTie,
        syncAllWidgets,
        renderReferenceBible,
        refresh: () => {
            renderActiveStrip();
            updateTelemetry();
            renderReferenceBible();
        },
        openBible: () => { bibleOpen = true; renderReferenceBible(); },
        usePersonalEngine: () => true,
        runPersonal: (st) => runSandTie(st),
        shouldLinkPrevHop: () => Boolean(flavors.link_prev_hop),
        hasActiveDials: () => ALL_DIAL_KEYS.some((k) => parseMultiValue(flavors[k]).length > 0),
        syncBlockToolbar: updateTelemetry,
    };
}

export function mountPersonalStudio(node, ctx) {
    return mountSandTieInStandard(node, ctx);
}

export function mountSandTieInStandard(node, ctx) {
    const planBtn = ctx.row?.querySelectorAll("button")?.[0] || null;
    const writeBtn = ctx.row?.querySelectorAll("button")?.[1] || null;
    const acceptBtn = ctx.row?.querySelectorAll("button")?.[2] || null;
    const hopTargetSel = ctx.row?.querySelector("select") || null;
    const sendHopBtn = ctx.row?.querySelectorAll("button")?.[3] || null;

    return createSandTieCore(node, {
        mountBody: ctx.body,
        briefEl: ctx.brief,
        planBox: ctx.planBox,
        blockBox: ctx.blockBox,
        say: ctx.say,
        saveDraft: ctx.saveDraft,
        getDurationLabel: () => String(widgetByName(node, "duration")?.value || "10 s"),
        getAspect: () => String(widgetByName(node, "aspect")?.value || widgetByName(node, "aspect_ratio")?.value || "16:9"),
        getRefPlan: () => String(widgetByName(node, "ref_plan")?.value || ""),
        setRefPlan: (v) => {
            const w = widgetByName(node, "ref_plan");
            if (w) {
                w.value = v;
                try { w.callback?.(v, node.graph?.canvas, node); } catch (_) {}
            }
            try { (node._h3Editor?.rail || node._h3Editor?.refRail)?.render?.(); } catch (_) {}
            try { ctx.onRefsChanged?.(); } catch (_) {}
        },
        getStartImage: ctx.startImage,
        getVoiceFiles: ctx.voiceFiles,
        previousHopContext: ctx.previousHopContext,
        setBusyState: ctx.setBusyState,
        isBusy: ctx.isBusy,
        standalone: false,
        onDialsChanged: ctx.onDialsChanged,
        legacyButtons: {
            beforeEl: ctx.brief,
            row: ctx.row,
            planBtn,
            writeBtn,
            acceptBtn,
            hopTargetSel,
            sendHopBtn,
            planCol: ctx.planBox?.parentElement || null,
            blockCol: ctx.blockBox?.parentElement || null,
        },
    });
}

export function mountSandTieStandalone(node, mountEl, { onSyncOutputs } = {}) {
    mountEl.textContent = "";
    const initState = readRigState(node);
    const status = el("div", "h3e-note h3e-writer-status");
    status.style.display = "none";
    const briefEl = el("textarea", "h3e-json");
    briefEl.rows = 2;
    briefEl.placeholder = "Describe the scene brief: who, where, what they do, camera, dialogue…";
    briefEl.value = String(widgetByName(node, "brief")?.value || "");

    const planBox = el("textarea", "h3e-json");
    planBox.rows = 8;
    planBox.value = initState.storyboard_out || "";
    const blockBox = el("textarea", "h3e-json");
    blockBox.rows = 12;
    blockBox.value = initState.prompt_out || "";

    const split = el("div", "h3e-standard-grid");
    const c1 = el("div", "h3e-standard-col");
    c1.append(el("div", "h3e-draft-meta", "Storyboard (Beats):"), planBox);
    const c2 = el("div", "h3e-standard-col");
    c2.append(el("div", "h3e-draft-meta", "H3 Prompt Output:"), blockBox);
    split.append(c1, c2);

    let busy = false;
    const planBtn = button("Plan", "Draft storyboard beats", () => core.runSandTie("plan"));
    const writeBtn = button("Write", "Write full H3 prompt from storyboard", () => core.runSandTie("write"));

    function commitW(name, val) {
        const w = widgetByName(node, name);
        if (!w) return;
        w.value = val;
        try { w.callback?.(val, node.graph?.canvas, node); } catch (_) {}
    }

    function applyOutputs() {
        const txt = blockBox.value.trim();
        commitW("brief", briefEl.value);
        patchRigState(node, {
            storyboard_out: planBox.value,
            prompt_out: txt,
        });
        onSyncOutputs?.(txt);
    }

    const core = createSandTieCore(node, {
        mountBody: mountEl,
        briefEl,
        planBox,
        blockBox,
        say: (txt, kind) => {
            status.style.display = txt ? "" : "none";
            status.className = "h3e-note h3e-writer-status" + (kind === "error" ? " h3e-note-error" : " h3e-note-hint");
            status.textContent = txt || "";
        },
        saveDraft: () => {
            commitW("brief", briefEl.value);
            patchRigState(node, {
                storyboard_out: planBox.value,
                prompt_out: blockBox.value,
            });
        },
        getDurationLabel: () => String(widgetByName(node, "duration")?.value || "10 s"),
        getAspect: () => {
            const wVal = Number(widgetByName(node, "width")?.value || 0);
            const hVal = Number(widgetByName(node, "height")?.value || 0);
            if (wVal > 0 && hVal > 0) return `${wVal}:${hVal}`;
            return String(widgetByName(node, "aspect")?.value || "16:9 landscape");
        },
        getRefPlan: () => readRigState(node).ref_plan_json || "",
        setRefPlan: (v) => patchRigState(node, { ref_plan_json: String(v || "") }),
        getStartImage: () => "",
        getVoiceFiles: () => [],
        previousHopContext: null,
        setBusyState: (v) => { busy = Boolean(v); planBtn.disabled = busy; writeBtn.disabled = busy; },
        isBusy: () => busy,
        standalone: true,
        onApplyStandalone: applyOutputs,
        legacyButtons: { planBtn, writeBtn, planCol: c1, blockCol: c2 },
    });

    mountEl.append(briefEl, status, split);
    return core;
}

export function mountSwapExtras(node, { body, wardInput, beforeEl }) {
    const row = el("div", "h3st-row");
    row.style.margin = "2px 0";
    const talkSel = el("select", "h3e-select");
    talkSel.title = "Optional SandTie Speech style for swapped dialogue";
    const styleSel = el("select", "h3e-select");
    styleSel.title = "Optional SandTie Visual Style overlay";
    const wardSel = el("select", "h3e-select");
    wardSel.title = "Quick wardrobe override from SandTie catalog";

    function fill(sel, placeholder, items) {
        sel.textContent = "";
        const ph = el("option", null, placeholder);
        ph.value = "";
        sel.appendChild(ph);
        for (const it of items || []) {
            const o = el("option", null, it.label);
            o.value = it.id;
            sel.appendChild(o);
        }
    }

    wardSel.addEventListener("change", () => {
        if (!wardSel.value) return;
        const opt = (_sharedCatalog?.wardrobe || []).find((x) => x.id === wardSel.value);
        if (opt && wardInput) wardInput.value = opt.label;
    });

    row.append(talkSel, styleSel, wardSel);
    if (beforeEl && beforeEl.parentElement === body) body.insertBefore(row, beforeEl);
    else body.appendChild(row);

    const hydrate = (cat) => {
        if (!cat) return;
        fill(talkSel, "Speech: Auto", cat.talkstyle);
        fill(styleSel, "Style: Clip Default", cat.style);
        fill(wardSel, "Wardrobe Quick Pick…", cat.wardrobe);
    };

    if (_sharedCatalog) hydrate(_sharedCatalog);
    else fetch(SANDTIE_OPTIONS_URL).then((r) => r.json()).then((j) => {
        if (j?.catalog) { _sharedCatalog = j.catalog; hydrate(_sharedCatalog); }
    }).catch(() => {});

    const resolveOpt = (key, id) => {
        if (!id) return "";
        const opt = (_sharedCatalog?.[key] || []).find((x) => x.id === id);
        return opt ? String(opt.prompt || opt.label || "") : "";
    };
    const readFields = () => ({
        sandtie_talkstyle: talkSel.value || "",
        sandtie_style: styleSel.value || "",
        talkstyle_rule: resolveOpt("talkstyle", talkSel.value),
        style_rule: resolveOpt("style", styleSel.value),
    });
    return {
        fields: readFields,
        extraPayload: readFields,
    };
}
