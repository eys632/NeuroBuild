from __future__ import annotations

import html
import json

from .models import GenerationResult, LayoutPlan, TeamReport


def completion_sound_html(
    event_id: int,
    enabled: bool = True,
    message: str = "대표님, 도면 설계가 완료되었습니다.",
) -> str:
    enabled_js = "true" if enabled else "false"
    message_js = json.dumps(message, ensure_ascii=False)
    return f"""
    <script>
      (() => {{
        const eventId = {int(event_id)};
        const enabled = {enabled_js};
        const message = {message_js};
        const eventKey = "__neurobuildLastVoiceEvent";
        if (!enabled) return;

        function parentDocument() {{
          try {{
            return window.parent && window.parent.document ? window.parent.document : null;
          }} catch (_) {{
            return null;
          }}
        }}

        function ensureAudio() {{
          if (window.__neurobuildAudio) return window.__neurobuildAudio;
          const AudioCtx = window.AudioContext || window.webkitAudioContext;
          if (!AudioCtx) return null;
          const audio = {{
            ctx: new AudioCtx(),
            unlocked: false
          }};
          audio.unlock = () => {{
            if (audio.ctx.state === "suspended") {{
              audio.ctx.resume().catch(() => {{}});
            }}
            audio.unlocked = true;
          }};
          try {{
            const parentDoc = parentDocument();
            document.addEventListener("pointerdown", audio.unlock, {{ capture: true, passive: true }});
            document.addEventListener("keydown", audio.unlock, {{ capture: true }});
            if (parentDoc) {{
              parentDoc.addEventListener("pointerdown", audio.unlock, {{ capture: true, passive: true }});
              parentDoc.addEventListener("keydown", audio.unlock, {{ capture: true }});
            }}
          }} catch (_) {{}}
          window.__neurobuildAudio = audio;
          return audio;
        }}

        function markPlayed() {{
          try {{
            if (window.sessionStorage.getItem(eventKey) === String(eventId)) return false;
            window.sessionStorage.setItem(eventKey, String(eventId));
          }} catch (_) {{
            if (window.__neurobuildLastVoiceEvent === eventId) return false;
            window.__neurobuildLastVoiceEvent = eventId;
          }}
          return true;
        }}

        function pickKoreanVoice(synth) {{
          const voices = synth.getVoices ? synth.getVoices() : [];
          return voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("ko"))
            || voices.find((voice) => /korean|한국|혜미|heami/i.test(voice.name))
            || null;
        }}

        function speak() {{
          const synth = window.speechSynthesis;
          if (!synth || !window.SpeechSynthesisUtterance) return false;
          const utterance = new SpeechSynthesisUtterance(message);
          const voice = pickKoreanVoice(synth);
          if (voice) utterance.voice = voice;
          utterance.lang = "ko-KR";
          utterance.rate = 0.95;
          utterance.pitch = 1.02;
          utterance.volume = 1;
          try {{
            synth.cancel();
            synth.speak(utterance);
            window.__neurobuildLastSpokenText = message;
            return true;
          }} catch (_) {{
            return false;
          }}
        }}

        function tone(ctx, start, freq, duration, gainLevel, type) {{
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = type;
          osc.frequency.setValueAtTime(freq, start);
          osc.frequency.exponentialRampToValueAtTime(freq * 1.018, start + duration);
          gain.gain.setValueAtTime(0.0001, start);
          gain.gain.exponentialRampToValueAtTime(gainLevel, start + 0.018);
          gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(start);
          osc.stop(start + duration + 0.025);
        }}

        function chime() {{
          const audio = ensureAudio();
          if (!audio) return;
          const ctx = audio.ctx;
          const schedule = () => {{
            const now = ctx.currentTime + 0.035;
            tone(ctx, now, 660, 0.16, 0.045, "sine");
            tone(ctx, now + 0.115, 990, 0.22, 0.040, "triangle");
            tone(ctx, now + 0.205, 1480, 0.18, 0.018, "sine");
          }};
          if (ctx.state === "suspended") {{
            ctx.resume().then(schedule).catch(() => {{}});
            return;
          }}
          schedule();
        }}

        function announce() {{
          if (!eventId || !markPlayed()) return;
          let announced = false;
          const trySpeak = () => {{
            if (announced) return;
            announced = true;
            speak();
            window.setTimeout(chime, 90);
          }};
          if (window.speechSynthesis && window.speechSynthesis.getVoices().length === 0) {{
            window.speechSynthesis.onvoiceschanged = trySpeak;
            window.setTimeout(trySpeak, 220);
            return;
          }}
          trySpeak();
        }}

        ensureAudio();
        window.setTimeout(announce, 240);
      }})();
    </script>
    """


def inject_global_css() -> str:
    return """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
      html, body, [class*="css"] { font-family: Inter, Pretendard, system-ui, sans-serif; }
      .stApp {
        background:
          linear-gradient(180deg, #0b0d10 0%, #11151a 44%, #0b0d10 100%);
        color:#eef2f6;
      }
      section[data-testid="stSidebar"] { display:none; }
      .block-container {
        max-width: 100% !important;
        padding-top: 1rem !important;
        padding-left: 1.2rem !important;
        padding-right:1.2rem !important;
      }
      div[data-testid="stTextArea"] textarea {
        background:#111820;
        border:1px solid #2e4858;
        color:#f8fafc;
        border-radius:8px;
      }
      .stButton button, .stDownloadButton button {
        min-height:42px;
        border-radius:8px;
        border:1px solid #345466;
        background:#173242;
        color:#e6fbff;
        font-weight:800;
      }
      .stButton button:hover, .stDownloadButton button:hover {
        border-color:#5eead4;
        color:#ffffff;
      }
      .metric-grid {
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
        margin:8px 0 18px;
      }
      .metric-card {
        padding:12px 14px;
        border-radius:8px;
        background:#121a22;
        border:1px solid #263846;
        min-height:78px;
      }
      .metric-card b { display:block; font-size:12px; color:#7dd3fc; margin-bottom:7px; }
      .metric-card span { font-size:20px; font-weight:900; color:#f8fafc; overflow-wrap:anywhere; }
      .report-card {
        border:1px solid #2b3b48;
        background:#111820;
        padding:14px 16px;
        border-radius:8px;
        margin-bottom:10px;
      }
      .report-card h4 { margin:0 0 8px 0; color:#5eead4; }
      .tiny { color:#a3b6c4; font-size:12px; }
      .brand-hero {
        position:relative;
        display:flex;
        align-items:center;
        gap:16px;
        min-height:118px;
        margin:6px 0 12px;
        padding:12px 4px 6px;
      }
      .brand-hero:before {
        content:"";
        position:absolute;
        left:88px;
        right:12px;
        bottom:10px;
        height:1px;
        background:linear-gradient(90deg, rgba(94,234,212,.72), rgba(125,211,252,.42), transparent);
        box-shadow:0 0 18px rgba(94,234,212,.35);
      }
      .brand-hero:after {
        content:"";
        position:absolute;
        left:112px;
        top:24px;
        width:min(38vw, 460px);
        height:76px;
        background:linear-gradient(90deg, rgba(94,234,212,.08), rgba(96,165,250,.08), transparent);
        filter:blur(18px);
        pointer-events:none;
      }
      .brand-orbit {
        position:relative;
        width:72px;
        height:72px;
        flex:0 0 72px;
        border-radius:50%;
        background:
          radial-gradient(circle at 45% 40%, rgba(248,250,252,.22), transparent 26%),
          radial-gradient(circle, rgba(94,234,212,.16), rgba(15,23,42,.68) 62%, rgba(15,23,42,.12));
        border:1px solid rgba(125,211,252,.48);
        box-shadow:
          0 0 18px rgba(94,234,212,.40),
          0 0 44px rgba(59,130,246,.20),
          inset 0 0 18px rgba(94,234,212,.16);
      }
      .brand-core {
        position:absolute;
        inset:13px;
        display:grid;
        place-items:center;
        border-radius:50%;
        color:#effcff;
        font-weight:900;
        font-size:18px;
        letter-spacing:.08em;
        background:#08121a;
        border:1px solid rgba(94,234,212,.52);
        text-shadow:0 0 12px rgba(94,234,212,.95);
      }
      .brand-orbit .ring {
        position:absolute;
        left:50%;
        top:50%;
        width:84px;
        height:18px;
        border:1px solid rgba(94,234,212,.54);
        border-left-color:transparent;
        border-right-color:transparent;
        border-radius:50%;
        transform:translate(-50%, -50%) rotate(-18deg);
        box-shadow:0 0 13px rgba(94,234,212,.32);
      }
      .brand-orbit .ring-b {
        width:76px;
        height:20px;
        border-color:rgba(125,211,252,.44);
        border-top-color:transparent;
        border-bottom-color:transparent;
        transform:translate(-50%, -50%) rotate(58deg);
      }
      .brand-copy { position:relative; z-index:1; min-width:0; }
      .brand-kicker {
        display:flex;
        align-items:center;
        gap:8px;
        margin-bottom:4px;
        color:#7dd3fc;
        font-size:11px;
        line-height:1;
        letter-spacing:.22em;
        font-weight:900;
      }
      .brand-kicker span {
        width:9px;
        height:9px;
        border-radius:50%;
        background:#5eead4;
        box-shadow:0 0 13px #5eead4;
      }
      .brand-title {
        position:relative;
        color:#f8feff;
        font-size:48px;
        line-height:.98;
        font-weight:900;
        letter-spacing:.01em;
        text-transform:none;
        text-shadow:
          0 0 8px rgba(94,234,212,.88),
          0 0 24px rgba(56,189,248,.55),
          0 0 52px rgba(96,165,250,.32);
      }
      .brand-title:before {
        content:attr(data-text);
        position:absolute;
        left:2px;
        top:0;
        color:#5eead4;
        opacity:.45;
        filter:blur(1px);
        clip-path:polygon(0 0, 100% 0, 100% 42%, 0 38%);
      }
      .brand-title:after {
        content:attr(data-text);
        position:absolute;
        left:-2px;
        top:0;
        color:#60a5fa;
        opacity:.28;
        clip-path:polygon(0 58%, 100% 62%, 100% 100%, 0 100%);
      }
      .brand-subline {
        display:flex;
        align-items:center;
        gap:9px;
        margin-top:9px;
        color:#f8d47a;
        font-size:11px;
        font-weight:900;
        letter-spacing:.18em;
      }
      .brand-subline i {
        display:block;
        width:46px;
        height:1px;
        background:linear-gradient(90deg, transparent, rgba(248,212,122,.9));
        box-shadow:0 0 11px rgba(248,212,122,.45);
      }
      .brand-subline i:last-child {
        background:linear-gradient(90deg, rgba(248,212,122,.9), transparent);
      }
      @media (max-width: 900px) {
        .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .brand-title { font-size:40px; }
        .brand-orbit { width:60px; height:60px; flex-basis:60px; }
      }
    </style>
    """


def department_world_html(active_team: str | None = None) -> str:
    teams = [
        ("기획팀", "요구사항 구조화", "brief", 9, 15, "#5eead4", "#38bdf8", 12, 8, "0s"),
        ("법무팀", "건축법 RAG", "rules", 56, 15, "#a5b4fc", "#60a5fa", -12, 8, "-1.25s"),
        ("예산팀", "공사비 리스크", "cost", 37, 37, "#f59e0b", "#fb7185", 10, -8, "-2.5s"),
        ("디자인팀", "공간 경험", "space", 9, 58, "#bef264", "#22c55e", 12, -8, "-3.75s"),
        ("설계팀", "BIM/IFC 생성", "ifc", 56, 58, "#7dd3fc", "#3b82f6", -12, -8, "-5s"),
    ]
    people = []
    for idx, (team, role, code, x, y, accent, accent2, dx, dy, delay) in enumerate(teams):
        hot = " active" if active_team == team else ""
        people.append(
            f"""
            <div class="person p{idx + 1}{hot}" style="--x:{x}%;--y:{y}%;--dx:{dx}px;--dy:{dy}px;--delay:{delay};--accent:{accent};--accent2:{accent2};">
              <span class="presence"></span>
              <span class="floor-shadow"></span>
              <div class="avatar">
                <i class="shoe left"></i>
                <i class="shoe right"></i>
                <i class="leg left"><em></em></i>
                <i class="leg right"><em></em></i>
                <i class="hand left"></i>
                <i class="hand right"></i>
                <i class="arm left"></i>
                <i class="arm right"></i>
                <i class="body">
                  <em class="lapel"></em>
                  <em class="badge"></em>
                </i>
                <i class="neck"></i>
                <i class="head">
                  <em class="hair"></em>
                  <em class="face"></em>
                </i>
              </div>
              <div class="nameplate"><b>{html.escape(team)}</b><span>{html.escape(role)}</span><small>{html.escape(code.upper())}</small></div>
            </div>
            """
        )

    return f"""
    <div id="hq">
      <div class="topbar">
        <span class="dot"></span><b>NEUROBUILD HQ</b><em>LIVE STANDUP</em>
      </div>
      <div class="floor">
        <div class="office-light l1"></div><div class="office-light l2"></div><div class="office-light l3"></div>
        <div class="zone zone1"><b>PLANNING</b><span>brief</span></div>
        <div class="zone zone2"><b>LEGAL</b><span>rules</span></div>
        <div class="zone zone3"><b>DESIGN</b><span>space</span></div>
        <div class="zone zone4"><b>BIM</b><span>ifc</span></div>
        <div class="zone zone5"><b>BUDGET</b><span>cost</span></div>
        <div class="desk d1"><i></i><span></span></div><div class="desk d2"><i></i><span></span></div>
        <div class="desk d3"><i></i><span></span></div><div class="desk d4"><i></i><span></span></div>
        <div class="meeting"><i></i><b></b><em></em></div>
        <div class="whiteboard wb1">RAG</div><div class="whiteboard wb2">IFC</div>
        <div class="plant pnt1"></div><div class="plant pnt2"></div>
        <div class="path path1"></div><div class="path path2"></div><div class="path path3"></div>
        {''.join(people)}
      </div>
      <div class="terminal">
        <b>CEO Command Queue</b>
        <p>요구사항 수신 -> 팀별 검토 -> BIM 생성 -> IFC export</p>
      </div>
    </div>
    <style>
      #hq {{
        position:relative; height:760px; overflow:hidden; border-radius:8px;
        background:#0b1117;
        border:1px solid #345064;
        box-shadow:0 18px 60px rgba(0,0,0,.36);
        font-family:Inter,Pretendard,sans-serif; color:#e2e8f0;
      }}
      #hq:before {{
        content:""; position:absolute; inset:0;
        background-image:
          linear-gradient(rgba(125,211,252,.06) 1px, transparent 1px),
          linear-gradient(90deg,rgba(125,211,252,.05) 1px, transparent 1px);
        background-size:30px 30px; opacity:.6; pointer-events:none;
      }}
      .topbar {{
        position:absolute; left:14px; right:14px; top:14px; height:46px;
        display:flex; align-items:center; gap:10px; padding:0 12px;
        border-radius:8px; background:#111b24; border:1px solid #3d6176; z-index:6;
      }}
      .topbar b {{ color:#7dd3fc; letter-spacing:.13em; font-size:13px; line-height:1.08; }}
      .topbar em {{ margin-left:auto; color:#f8d47a; font-style:normal; font-size:11px; font-weight:900; white-space:nowrap; }}
      .dot {{ width:9px; height:9px; border-radius:50%; background:#22c55e; box-shadow:0 0 12px #22c55e; }}
      .floor {{
        position:absolute; left:16px; right:16px; top:76px; bottom:112px;
        border:1px solid rgba(125,211,252,.34);
        background:
          linear-gradient(180deg, rgba(14,25,32,.98), rgba(7,13,20,.98));
        box-shadow:
          0 0 0 1px rgba(255,255,255,.02) inset,
          0 0 56px rgba(20,184,166,.10) inset;
        overflow:hidden;
      }}
      .floor:before {{
        content:""; position:absolute; inset:0; background-size:54px 54px;
        background-image:
          linear-gradient(rgba(125,211,252,.09) 1px, transparent 1px),
          linear-gradient(90deg,rgba(125,211,252,.08) 1px, transparent 1px);
      }}
      .floor:after {{
        content:""; position:absolute; left:0; right:0; top:51%; height:1px;
        background:linear-gradient(90deg, transparent, rgba(148,163,184,.30), transparent);
      }}
      .office-light {{
        position:absolute; left:8%; top:4%; width:24%; height:22px; border-radius:999px;
        background:linear-gradient(90deg, transparent, rgba(224,242,254,.16), transparent);
        box-shadow:0 0 28px rgba(125,211,252,.18); z-index:1;
      }}
      .l2 {{ left:38%; width:23%; }} .l3 {{ left:68%; width:22%; }}
      .zone {{
        position:absolute; border:1px solid rgba(148,163,184,.24);
        background:rgba(2,6,23,.20);
        color:rgba(226,232,240,.72); padding:9px;
        z-index:1;
      }}
      .zone b {{ display:block; font-size:11px; letter-spacing:.14em; color:#cfe8f7; }}
      .zone span {{ display:block; margin-top:3px; font-size:9px; color:#7dd3fc; text-transform:uppercase; }}
      .zone1 {{ left:4%; top:5%; width:37%; height:34%; }}
      .zone2 {{ left:46%; top:5%; width:47%; height:34%; }}
      .zone3 {{ left:4%; top:51%; width:37%; height:40%; }}
      .zone4 {{ left:46%; top:51%; width:25%; height:40%; }}
      .zone5 {{ left:74%; top:51%; width:19%; height:40%; }}
      .desk {{
        position:absolute; width:64px; height:34px; border-radius:8px;
        background:linear-gradient(180deg,#33495b,#203241);
        border:1px solid rgba(125,211,252,.28);
        box-shadow:0 12px 24px rgba(0,0,0,.24);
        z-index:3;
      }}
      .desk i {{ position:absolute; left:9px; top:-9px; width:28px; height:14px; border-radius:4px; background:#09131b; border:1px solid rgba(125,211,252,.28); }}
      .desk span {{ position:absolute; right:8px; top:9px; width:16px; height:10px; border-radius:3px; background:rgba(94,234,212,.35); }}
      .d1 {{ left:25%; top:25%; }} .d2 {{ left:63%; top:25%; }} .d3 {{ left:22%; top:70%; }} .d4 {{ left:63%; top:70%; }}
      .meeting {{ position:absolute; left:38%; top:40%; width:84px; height:48px; border-radius:18px; background:rgba(51,65,85,.64); border:1px solid rgba(125,211,252,.25); z-index:3; }}
      .meeting i,.meeting b,.meeting em {{ position:absolute; display:block; width:16px; height:16px; border-radius:50%; background:rgba(94,234,212,.42); }}
      .meeting i {{ left:12px; top:13px; }} .meeting b {{ left:41px; top:7px; }} .meeting em {{ right:10px; top:24px; }}
      .whiteboard {{ position:absolute; width:62px; height:18px; border-radius:6px; background:#5eead4; color:#020617; font-size:10px; line-height:18px; font-weight:900; text-align:center; box-shadow:0 0 18px rgba(94,234,212,.45); z-index:4; }}
      .wb1 {{ left:71%; top:16%; }} .wb2 {{ left:59%; top:48%; }}
      .path {{ position:absolute; height:3px; border-radius:999px; background:rgba(94,234,212,.44); box-shadow:0 0 15px rgba(94,234,212,.28); z-index:2; }}
      .path1 {{ left:23%; top:45%; width:30%; transform:rotate(17deg); }}
      .path2 {{ left:43%; top:42%; width:24%; transform:rotate(-18deg); background:rgba(96,165,250,.45); }}
      .path3 {{ left:55%; top:57%; width:28%; transform:rotate(12deg); background:rgba(248,212,122,.48); }}
      .plant {{ position:absolute; width:18px; height:22px; border-radius:0 0 6px 6px; background:#1f2937; border:1px solid rgba(125,211,252,.20); z-index:4; }}
      .plant:before {{ content:""; position:absolute; left:-4px; top:-10px; width:26px; height:15px; border-radius:50%; background:rgba(34,197,94,.56); }}
      .pnt1 {{ left:7%; top:42%; }} .pnt2 {{ right:7%; bottom:7%; }}
      .person {{
        position:absolute; left:var(--x); top:var(--y); width:102px; height:136px;
        transform:translate3d(0,0,0);
        animation:patrol 8.2s infinite ease-in-out;
        animation-delay:var(--delay);
        z-index:20;
      }}
      .person.active .presence {{ opacity:1; border-color:#facc15; box-shadow:0 0 0 1px rgba(250,204,21,.30), 0 0 34px rgba(250,204,21,.34); }}
      .person.active .nameplate {{ border-color:#facc15; box-shadow:0 0 0 1px rgba(250,204,21,.24), 0 16px 34px rgba(0,0,0,.38); }}
      .presence {{
        position:absolute; left:9px; top:16px; width:56px; height:67px; border-radius:40% 40% 48% 48%;
        border:1px solid color-mix(in srgb, var(--accent) 46%, transparent);
        background:radial-gradient(circle at 45% 40%, color-mix(in srgb, var(--accent) 13%, transparent), transparent 63%);
        opacity:.66; animation:presencePulse 2.6s infinite ease-in-out;
      }}
      .floor-shadow {{
        position:absolute; left:15px; top:84px; width:50px; height:14px; border-radius:50%;
        background:rgba(0,0,0,.44); filter:blur(2px);
        animation:shadowStep .68s infinite alternate ease-in-out;
      }}
      .avatar {{
        position:absolute; left:13px; top:15px; width:54px; height:90px;
        animation:walkBob .68s infinite alternate ease-in-out;
        filter:drop-shadow(0 0 12px color-mix(in srgb, var(--accent) 42%, transparent));
      }}
      .avatar i, .avatar em {{ position:absolute; display:block; }}
      .head {{
        left:15px; top:0; width:28px; height:30px; border-radius:48% 48% 44% 44%;
        background:linear-gradient(180deg,#ffd89d,#e7a468);
        border:2px solid rgba(255,255,255,.78);
        box-shadow:inset 0 -5px 0 rgba(120,53,15,.16);
        animation:headTurn 3.2s infinite ease-in-out;
      }}
      .hair {{
        left:1px; right:1px; top:-3px; height:12px; border-radius:18px 18px 8px 8px;
        background:linear-gradient(180deg,#243044,#111827);
      }}
      .face {{
        left:8px; top:15px; width:12px; height:7px; border-radius:999px;
        border-top:2px solid rgba(120,53,15,.32);
      }}
      .neck {{ left:26px; top:28px; width:9px; height:9px; border-radius:3px; background:#e5a56c; }}
      .body {{
        left:11px; top:35px; width:36px; height:36px; border-radius:12px 12px 9px 9px;
        background:linear-gradient(155deg, var(--accent), var(--accent2));
        border:1px solid rgba(255,255,255,.36);
        box-shadow:inset 0 6px 12px rgba(255,255,255,.16), inset 0 -10px 16px rgba(2,6,23,.16);
      }}
      .lapel {{
        left:9px; right:9px; top:9px; height:3px; border-radius:999px;
        background:rgba(255,255,255,.68);
      }}
      .badge {{
        right:7px; top:18px; width:6px; height:6px; border-radius:50%;
        background:#e0f2fe; box-shadow:0 0 8px rgba(224,242,254,.55);
      }}
      .arm {{
        top:38px; width:8px; height:33px; border-radius:999px;
        background:linear-gradient(180deg,#dbeafe,#8db6ec);
        transform-origin:50% 10%;
        box-shadow:inset 0 -7px 10px rgba(30,64,175,.18);
      }}
      .arm.left {{ left:4px; animation:leftArm .68s infinite alternate ease-in-out; }}
      .arm.right {{ right:3px; animation:rightArm .68s infinite alternate ease-in-out; }}
      .hand {{
        top:68px; width:8px; height:8px; border-radius:50%; background:#ffd097; z-index:4;
      }}
      .hand.left {{ left:0; animation:leftHand .68s infinite alternate ease-in-out; }}
      .hand.right {{ right:0; animation:rightHand .68s infinite alternate ease-in-out; }}
      .leg {{
        top:67px; width:10px; height:28px; border-radius:999px;
        background:linear-gradient(180deg,#2563eb,#1d4ed8);
        transform-origin:50% 5%;
      }}
      .leg em {{
        left:2px; bottom:-2px; width:7px; height:14px; border-radius:999px;
        background:#1e40af;
      }}
      .leg.left {{ left:17px; animation:leftLeg .68s infinite alternate ease-in-out; }}
      .leg.right {{ right:11px; animation:rightLeg .68s infinite alternate ease-in-out; }}
      .shoe {{
        top:91px; width:18px; height:7px; border-radius:999px;
        background:linear-gradient(90deg,#5eead4,#38bdf8);
        box-shadow:0 0 9px rgba(94,234,212,.46);
      }}
      .shoe.left {{ left:10px; animation:leftShoe .68s infinite alternate ease-in-out; }}
      .shoe.right {{ right:6px; animation:rightShoe .68s infinite alternate ease-in-out; }}
      .nameplate {{
        position:absolute; left:0; top:98px; width:88px; min-height:38px;
        padding:7px 8px; border-radius:8px;
        background:rgba(5,12,18,.95); border:1px solid color-mix(in srgb, var(--accent) 62%, #334155);
        box-shadow:0 14px 30px rgba(0,0,0,.30);
      }}
      .nameplate:before {{
        content:""; position:absolute; left:34px; top:-7px; width:12px; height:12px; transform:rotate(45deg);
        background:rgba(5,12,18,.95);
        border-left:1px solid color-mix(in srgb, var(--accent) 62%, #334155);
        border-top:1px solid color-mix(in srgb, var(--accent) 62%, #334155);
      }}
      .nameplate b {{ display:block; font-size:13px; line-height:1.1; color:#f8fafc; letter-spacing:.02em; }}
      .nameplate span {{ display:block; margin-top:4px; font-size:9px; line-height:1.16; color:#c7dcec; white-space:normal; }}
      .nameplate small {{
        position:absolute; right:8px; top:7px; font-size:8px; letter-spacing:.08em; color:var(--accent);
        opacity:.86;
      }}
      .terminal {{
        position:absolute; left:14px; right:14px; bottom:14px; padding:14px 16px; border-radius:8px;
        background:#101820; border:1px solid #38566a;
      }}
      .terminal b {{ color:#5eead4; font-size:18px; }} .terminal p {{ margin:7px 0 0; color:#e2e8f0; font-size:13px; }}
      @keyframes patrol {{
        0%, 100% {{ transform:translate(0,0); }}
        34% {{ transform:translate(calc(var(--dx) * .55), calc(var(--dy) * .45)); }}
        68% {{ transform:translate(calc(var(--dx) * -.36), calc(var(--dy) * .33)); }}
      }}
      @keyframes walkBob {{ 0% {{ transform:translateY(0) rotate(-1deg); }} 100% {{ transform:translateY(-5px) rotate(1deg); }} }}
      @keyframes shadowStep {{ to {{ transform:scaleX(.82); opacity:.62; }} }}
      @keyframes presencePulse {{ 50% {{ transform:scale(1.06); opacity:.92; }} }}
      @keyframes headTurn {{ 0%,100% {{ transform:translateX(0); }} 50% {{ transform:translateX(2px); }} }}
      @keyframes leftArm {{ from {{ transform:rotate(17deg); }} to {{ transform:rotate(-26deg); }} }}
      @keyframes rightArm {{ from {{ transform:rotate(-24deg); }} to {{ transform:rotate(18deg); }} }}
      @keyframes leftHand {{ from {{ transform:translate(5px,1px); }} to {{ transform:translate(-3px,-3px); }} }}
      @keyframes rightHand {{ from {{ transform:translate(-4px,-2px); }} to {{ transform:translate(5px,2px); }} }}
      @keyframes leftLeg {{ from {{ transform:rotate(-18deg); }} to {{ transform:rotate(16deg); }} }}
      @keyframes rightLeg {{ from {{ transform:rotate(17deg); }} to {{ transform:rotate(-16deg); }} }}
      @keyframes leftShoe {{ from {{ transform:translateX(-5px); }} to {{ transform:translateX(5px); }} }}
      @keyframes rightShoe {{ from {{ transform:translateX(5px); }} to {{ transform:translateX(-5px); }} }}
    </style>
    """


def viewer_html(plan: LayoutPlan, ifc_text: str) -> str:
    plan_json = json.dumps(plan.to_dict(), ensure_ascii=False).replace("</", "<\\/")
    ifc_json = json.dumps(ifc_text or "", ensure_ascii=False).replace("</", "<\\/")
    template = """
    <div id="nb-viewer">
      <div id="viewer-hud"><b>NEUROBUILD BIM VIEWER</b><span id="status">실제 IFC 로딩 준비 중</span></div>
      <div id="viewer-tools">
        <button id="btnIso">ISO</button><button id="btnTop">TOP</button><button id="btnRoof">ROOF</button><button id="btnXray">X-RAY</button><button id="btnFit">FIT</button>
      </div>
      <div id="canvas-root"></div>
    </div>
    <script type="importmap">
      {"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/","web-ifc":"https://cdn.jsdelivr.net/npm/web-ifc@0.0.77/web-ifc-api.js","three-mesh-bvh":"https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.7.0/build/index.module.js"}}
    </script>
    <script type="module">
      import * as THREE from 'three';
      import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
      import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

      const plan = __PLAN_JSON__;
      const ifcText = __IFC_JSON__;
      const root = document.getElementById('canvas-root');
      const statusEl = document.getElementById('status');
      const HEIGHT = 760;
      const FLOOR_HEIGHT = 3.18;
      const floorCount = Math.max(1, Number(plan.floors || 1));
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a1016);
      scene.fog = new THREE.Fog(0x0a1016, 44, 96);
      const camera = new THREE.PerspectiveCamera(42, Math.max(root.clientWidth, 1) / HEIGHT, 0.1, 2000);
      camera.position.set(plan.width * .9, 9 + floorCount * 2.4, plan.depth * 1.7);
      const renderer = new THREE.WebGLRenderer({ antialias:true, powerPreference:'high-performance' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(Math.max(root.clientWidth, 1), HEIGHT);
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      root.appendChild(renderer.domElement);
      const pmrem = new THREE.PMREMGenerator(renderer);
      scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.target.set(plan.width/2, Math.max(1.1, (floorCount - 1) * FLOOR_HEIGHT / 2 + 1.4), plan.depth/2);
      controls.enableDamping = true;
      controls.dampingFactor = .065;
      controls.minDistance = 4;
      controls.maxDistance = 75;
      controls.maxPolarAngle = Math.PI * .49;
      scene.add(new THREE.HemisphereLight(0xeaf8ff, 0x111827, 1.45));
      const sun = new THREE.DirectionalLight(0xffffff, 2.55);
      sun.position.set(-8,18,9);
      sun.castShadow=true;
      sun.shadow.mapSize.set(2048,2048);
      sun.shadow.camera.left=-30;
      sun.shadow.camera.right=30;
      sun.shadow.camera.top=30;
      sun.shadow.camera.bottom=-30;
      scene.add(sun);
      const fill = new THREE.DirectionalLight(0x7dd3fc,.7);
      fill.position.set(12,8,-14);
      scene.add(fill);
      const world = new THREE.Group();
      scene.add(world);
      const roofGroup = new THREE.Group();
      let wallMeshes=[];
      let fitObject=world;
      let roofVisible=true;
      let xray=false;
      const mats = {
        base:new THREE.MeshStandardMaterial({color:0x334155,roughness:.92}),
        floor:new THREE.MeshStandardMaterial({color:0x475569,roughness:.82}),
        ext:new THREE.MeshStandardMaterial({color:0xe9eef7,roughness:.58}),
        int:new THREE.MeshStandardMaterial({color:0xf6f0df,roughness:.72}),
        living:new THREE.MeshStandardMaterial({color:0x4ade80,transparent:true,opacity:.18,side:THREE.DoubleSide}),
        bedroom:new THREE.MeshStandardMaterial({color:0x60a5fa,transparent:true,opacity:.16,side:THREE.DoubleSide}),
        bath:new THREE.MeshStandardMaterial({color:0xc084fc,transparent:true,opacity:.17,side:THREE.DoubleSide}),
        kitchen:new THREE.MeshStandardMaterial({color:0xfbbf24,transparent:true,opacity:.15,side:THREE.DoubleSide}),
        glass:new THREE.MeshPhysicalMaterial({color:0x67e8f9,transparent:true,opacity:.52,roughness:.02,transmission:.35,thickness:.05}),
        door:new THREE.MeshStandardMaterial({color:0xb7791f,roughness:.58}),
        roof:new THREE.MeshStandardMaterial({color:0x94a3b8,transparent:true,opacity:.28,roughness:.62}),
        wood:new THREE.MeshStandardMaterial({color:0x9a5a18,roughness:.72}),
        green:new THREE.MeshStandardMaterial({color:0x14b8a6,roughness:.58}),
        dark:new THREE.MeshStandardMaterial({color:0x111827,roughness:.85}),
        white:new THREE.MeshStandardMaterial({color:0xf8fafc,roughness:.38})
      };
      function setStatus(t){ statusEl.textContent=t; }
      function box(group,name,w,h,d,x,y,z,mat,cast=true){
        const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);
        m.name=name; m.position.set(x,y,z); m.castShadow=cast; m.receiveShadow=true; group.add(m); return m;
      }
      function edges(mesh,color=0x0f172a,opacity=.32){
        const e=new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry,30),new THREE.LineBasicMaterial({color,transparent:true,opacity}));
        e.position.copy(mesh.position); e.rotation.copy(mesh.rotation); e.scale.copy(mesh.scale); mesh.parent.add(e); return e;
      }
      function label(text,sub){
        const c=document.createElement('canvas'); c.width=512; c.height=170; const ctx=c.getContext('2d');
        round(ctx,16,18,480,128,16); ctx.fillStyle='rgba(2,6,23,.78)'; ctx.fill(); ctx.strokeStyle='rgba(125,211,252,.58)'; ctx.lineWidth=3; ctx.stroke();
        ctx.fillStyle='#e0f2fe'; ctx.font='bold 40px Arial'; ctx.textAlign='center'; ctx.fillText(text,256,76);
        ctx.fillStyle='#bae6fd'; ctx.font='27px Arial'; ctx.fillText(sub||'',256,116);
        const tex=new THREE.CanvasTexture(c); tex.colorSpace=THREE.SRGBColorSpace;
        const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,transparent:true,depthTest:false}));
        s.scale.set(1.8,.6,1); return s;
      }
      function round(ctx,x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }
      function matForRoom(k){ return k==='living'?mats.living:k==='bedroom'?mats.bedroom:k==='bath'?mats.bath:k==='kitchen'?mats.kitchen:mats.floor; }
      function floorY(item){ return (Math.max(1, Number(item.floor || 1)) - 1) * FLOOR_HEIGHT; }
      function addFurniture(r){
        const g=new THREE.Group(); world.add(g); const fy=floorY(r); const cx=r.x+r.width/2, cz=r.y+r.depth/2;
        if(r.kind==='living'){ box(g,'sofa',Math.min(3.4,r.width*.55),.55,.82,cx-r.width*.08,fy+.34,cz+r.depth*.16,mats.green); box(g,'table',1.7,.14,.95,cx,fy+.42,cz-.08,mats.wood); box(g,'media',2.4,1.1,.1,r.x+.16,fy+.72,cz,mats.dark,false); }
        if(r.kind==='bedroom'){ box(g,'bed',1.3,.35,1.95,r.x+r.width*.36,fy+.25,r.y+r.depth*.58,mats.wood); box(g,'mattress',1.18,.20,1.72,r.x+r.width*.36,fy+.55,r.y+r.depth*.58,mats.white); box(g,'desk',.88,.12,.5,r.x+r.width*.78,fy+.74,r.y+r.depth*.25,mats.wood); }
        if(r.kind==='kitchen'){ box(g,'counter',r.width*.82,.86,.58,cx,fy+.43,r.y+.38,mats.wood); box(g,'island',Math.min(2.0,r.width*.55),.86,.82,cx,fy+.43,cz+.35,mats.dark); }
        if(r.kind==='bath'){ box(g,'vanity',.72,.7,.42,r.x+.5,fy+.36,r.y+.38,mats.white); box(g,'shower',.72,1.75,.72,r.x+r.width-.55,fy+.88,r.y+r.depth-.52,mats.glass,false); }
      }
      function baseScene(){
        const plane=box(scene,'site',Math.max(plan.width+10,24),.08,Math.max(plan.depth+10,24),plan.width/2,-.31,plan.depth/2,mats.dark,false);
        plane.receiveShadow=true;
        const grid=new THREE.GridHelper(Math.max(plan.width,plan.depth)+8,36,0x38bdf8,0x263746);
        grid.position.set(plan.width/2,-.25,plan.depth/2);
        grid.material.transparent=true; grid.material.opacity=.38; scene.add(grid);
      }
      function buildPreview(){
        setStatus('IFC 로딩 실패 또는 제한: 고품질 BIM 프리뷰 표시');
        const fd=box(world,'foundation',plan.width+.42,.28,plan.depth+.42,plan.width/2,-.12,plan.depth/2,mats.base); edges(fd,0x67e8f9,.24);
        for(let floor=1; floor<=floorCount; floor++){
          const fy=(floor-1)*FLOOR_HEIGHT;
          const fl=box(world,`${floor}F floor`,plan.width,.14,plan.depth,plan.width/2,fy+.02,plan.depth/2,mats.floor);
          edges(fl,0x93c5fd,.25);
          const floorTag=label(`${floor}F`, floor===1?'공용부 / 현관':'침실 / 라운지');
          floorTag.position.set(.85,fy+2.65,.65); world.add(floorTag);
        }
        for(const r of plan.rooms){
          const fy=floorY(r);
          const zone=new THREE.Mesh(new THREE.PlaneGeometry(r.width-.06,r.depth-.06), matForRoom(r.kind));
          zone.rotation.x=-Math.PI/2; zone.position.set(r.x+r.width/2,fy+.105,r.y+r.depth/2); world.add(zone);
          const sp=label(r.name,`${Number(r.area).toFixed(1)}㎡`); sp.position.set(r.x+r.width/2,fy+.40,r.y+r.depth/2); world.add(sp);
          addFurniture(r);
        }
        for(const w of plan.walls){
          const fy=floorY(w);
          const dx=w.x2-w.x1, dz=w.y2-w.y1, len=Math.hypot(dx,dz);
          const m=box(world,w.name,len,w.height,w.thickness,(w.x1+w.x2)/2,fy+w.height/2,(w.y1+w.y2)/2,w.wall_type==='external'?mats.ext:mats.int);
          m.rotation.y=-Math.atan2(dz,dx); wallMeshes.push(m); edges(m,0x334155,.32);
        }
        for(const o of plan.openings){
          const fy=floorY(o);
          const mat=o.kind==='window'?mats.glass:mats.door;
          const thick=o.kind==='window'?.12:.14;
          const m=box(world,o.name,o.width,o.height,thick,o.x,fy+o.sill_height+o.height/2,o.y,mat,false);
          m.rotation.y=-o.rotation_deg*Math.PI/180; edges(m,o.kind==='window'?0x7dd3fc:0xf59e0b,.9);
        }
        const roof=box(roofGroup,'roof',plan.width+.44,.14,plan.depth+.44,plan.width/2,(floorCount-1)*FLOOR_HEIGHT+3.04,plan.depth/2,mats.roof,false);
        edges(roof,0xe0f2fe,.28); world.add(roofGroup); fitObject=world;
      }
      async function tryIFC(){
        if(!ifcText || ifcText.length<100) return false;
        try{
          setStatus('생성된 IFC를 web-ifc 로더로 읽는 중');
          const mod=await import('https://cdn.jsdelivr.net/npm/web-ifc-three@0.0.126/IFCLoader.js');
          const loader=new mod.IFCLoader();
          await loader.ifcManager.setWasmPath('https://cdn.jsdelivr.net/npm/web-ifc@0.0.77/', true);
          if(loader.ifcManager.applyWebIfcConfig) await loader.ifcManager.applyWebIfcConfig({COORDINATE_TO_ORIGIN:false, USE_FAST_BOOLS:true});
          const blob=new Blob([ifcText],{type:'application/octet-stream'});
          const url=URL.createObjectURL(blob);
          const model=await loader.loadAsync(url);
          URL.revokeObjectURL(url);
          model.name='Neurobuild IFC Model';
          model.traverse(o=>{ if(o.isMesh){ o.castShadow=true; o.receiveShadow=true; if(o.material){ o.material.side=THREE.DoubleSide; o.material.needsUpdate=true; } } });
          world.add(model); fitObject=model; setStatus('실제 IFC 모델 로딩 완료'); return true;
        }catch(err){
          console.warn('IFC loader failed',err);
          return false;
        }
      }
      function fit(obj=fitObject, mode='iso'){
        const box3=new THREE.Box3().setFromObject(obj);
        if(!Number.isFinite(box3.min.x)||box3.isEmpty()){
          camera.position.set(plan.width*.9,12,plan.depth*1.7); controls.target.set(plan.width/2,1.1,plan.depth/2); controls.update(); return;
        }
        const c=box3.getCenter(new THREE.Vector3());
        const s=box3.getSize(new THREE.Vector3());
        const max=Math.max(s.x,s.y,s.z,1);
        const dist=max/(2*Math.tan(camera.fov*Math.PI/360))*1.45;
        if(mode==='top') camera.position.set(c.x,c.y+dist*1.18,c.z+.01);
        else camera.position.set(c.x+dist*.72,c.y+dist*.52,c.z+dist*.86);
        controls.target.copy(c); controls.update();
      }
      function toggleXray(){
        xray=!xray;
        for(const m of wallMeshes){ m.material.transparent=xray; m.material.opacity=xray ? .32 : 1; m.material.needsUpdate=true; }
      }
      baseScene();
      const loaded=await tryIFC();
      if(!loaded) buildPreview();
      fit(fitObject,'iso');
      document.getElementById('btnIso').onclick=()=>fit(fitObject,'iso');
      document.getElementById('btnTop').onclick=()=>fit(fitObject,'top');
      document.getElementById('btnFit').onclick=()=>fit(fitObject,'iso');
      document.getElementById('btnRoof').onclick=()=>{ roofVisible=!roofVisible; roofGroup.visible=roofVisible; };
      document.getElementById('btnXray').onclick=toggleXray;
      function animate(){ requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); }
      animate();
      window.addEventListener('resize',()=>{ const w=Math.max(root.clientWidth,1); camera.aspect=w/HEIGHT; camera.updateProjectionMatrix(); renderer.setSize(w,HEIGHT); });
    </script>
    <style>
      #nb-viewer{position:relative;height:800px;overflow:hidden;border-radius:8px;border:1px solid #2b3e4d;background:#0a1016;box-shadow:0 18px 60px rgba(0,0,0,.36);}
      #canvas-root{height:760px;width:100%;}
      #viewer-hud{position:absolute;z-index:5;left:14px;top:14px;min-width:300px;padding:11px 13px;border-radius:8px;background:rgba(8,13,18,.82);color:#e0f2fe;border:1px solid rgba(125,211,252,.35);font-family:Inter,Pretendard,sans-serif;font-size:12px;line-height:1.55;}
      #viewer-hud b{display:block;color:#7dd3fc;letter-spacing:.16em;margin-bottom:4px;}
      #viewer-tools{position:absolute;z-index:6;right:14px;top:14px;display:flex;gap:7px;padding:7px;border-radius:8px;background:rgba(8,13,18,.80);border:1px solid rgba(148,163,184,.24);}
      #viewer-tools button{cursor:pointer;border:1px solid rgba(125,211,252,.34);background:#173242;color:#e0f2fe;border-radius:8px;padding:8px 10px;font-weight:900;font-size:11px;letter-spacing:.06em;}
      #viewer-tools button:hover{border-color:#5eead4;}
    </style>
    """
    return template.replace("__PLAN_JSON__", plan_json).replace("__IFC_JSON__", ifc_json)


def plan_svg(plan: LayoutPlan) -> str:
    scale = 46 if plan.floors > 1 else 48
    w = int(plan.width * scale)
    floor_h = int(plan.depth * scale)
    gap = 58
    h = floor_h * plan.floors + gap * (plan.floors - 1)
    rooms_svg = []
    colors = {"living": "#22c55e", "bedroom": "#3b82f6", "kitchen": "#f59e0b", "bath": "#a855f7", "service": "#94a3b8"}
    floor_backdrops = []
    for floor in range(1, plan.floors + 1):
        y0 = (floor - 1) * (floor_h + gap)
        floor_backdrops.append(
            f'<g><rect x="0" y="{y0}" width="{w}" height="{floor_h}" fill="url(#grid)" />'
            f'<rect x="4" y="{y0 + 4}" width="{w - 8}" height="{floor_h - 8}" fill="none" stroke="#38bdf8" stroke-opacity="0.26" stroke-width="2" rx="8"/>'
            f'<text x="16" y="{y0 + 30}" fill="#5eead4" font-size="22" font-weight="900">{floor}F</text></g>'
        )
    for r in plan.rooms:
        y0 = (max(1, r.floor) - 1) * (floor_h + gap)
        x, y, rw, rh = r.x * scale, y0 + r.y * scale, r.width * scale, r.depth * scale
        color = colors.get(r.kind, "#64748b")
        rooms_svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="{color}" opacity="0.22" stroke="{color}" stroke-width="2" rx="6"/>')
        rooms_svg.append(f'<text x="{x + 10:.1f}" y="{y + 24:.1f}" fill="#e5edf9" font-size="14" font-weight="800">{html.escape(r.name)}</text>')
        rooms_svg.append(f'<text x="{x + 10:.1f}" y="{y + 43:.1f}" fill="#bae6fd" font-size="12">{r.area:.1f}㎡</text>')
    walls_svg = []
    for wall in plan.walls:
        y0 = (max(1, wall.floor) - 1) * (floor_h + gap)
        walls_svg.append(f'<line x1="{wall.x1 * scale:.1f}" y1="{y0 + wall.y1 * scale:.1f}" x2="{wall.x2 * scale:.1f}" y2="{y0 + wall.y2 * scale:.1f}" stroke="#f8fafc" stroke-width="{max(4, wall.thickness * scale):.1f}" stroke-linecap="round" opacity="0.92"/>')
    openings_svg = []
    for opening in plan.openings:
        y0 = (max(1, opening.floor) - 1) * (floor_h + gap)
        color = "#38bdf8" if opening.kind == "window" else "#f59e0b"
        size = opening.width * scale
        if abs(opening.rotation_deg) % 180 == 90:
            openings_svg.append(f'<line x1="{opening.x * scale:.1f}" y1="{y0 + (opening.y * scale) - size / 2:.1f}" x2="{opening.x * scale:.1f}" y2="{y0 + (opening.y * scale) + size / 2:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
        else:
            openings_svg.append(f'<line x1="{(opening.x * scale) - size / 2:.1f}" y1="{y0 + opening.y * scale:.1f}" x2="{(opening.x * scale) + size / 2:.1f}" y2="{y0 + opening.y * scale:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
    return f"""
    <div style="overflow:auto;border-radius:8px;border:1px solid #2b3e4d;background:#0b1118;padding:12px;">
      <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto;background:#111827;border-radius:8px;">
        <defs><pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M 48 0 L 0 0 0 48" fill="none" stroke="#334155" stroke-width="1"/></pattern></defs>
        {''.join(floor_backdrops)}
        {''.join(rooms_svg)}
        {''.join(walls_svg)}
        {''.join(openings_svg)}
      </svg>
    </div>
    """


def report_card(report: TeamReport) -> str:
    status = "LLM" if report.used_llm else "Fallback"
    warnings = "".join(f"<li>{html.escape(w)}</li>" for w in report.warnings)
    warn_html = f"<ul>{warnings}</ul>" if warnings else ""
    model = report.model or ""
    return f"""
    <div class="report-card">
      <h4>{html.escape(report.team)} <span class="tiny">{status} · {html.escape(model)}</span></h4>
      <div>{html.escape(report.summary).replace(chr(10), '<br/>')}</div>
      {warn_html}
    </div>
    """


def metrics_html(result: GenerationResult) -> str:
    p = result.plan
    b = result.brief
    cards = [
        ("연면적", f"{p.gross_area:.1f}㎡"),
        ("층수", f"{p.floors}층"),
        ("예상 공사비", f"{p.estimated_cost_krw:,}원"),
        ("예산 상태", p.budget_status),
        ("침실 / 거주자", f"{b.room_count}개 / {b.occupants}명"),
    ]
    return "<div class='metric-grid'>" + "".join(
        f"<div class='metric-card'><b>{html.escape(k)}</b><span>{html.escape(v)}</span></div>" for k, v in cards
    ) + "</div>"
