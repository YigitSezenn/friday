"""Kamera + el hareketiyle pencere taşıma. Açmadan önce kullanıcıdan sesli onay ister."""

from __future__ import annotations

from tools.actions import confirm

KIND = "hand_control"


def _summary(model_ready: bool) -> str:
    note = "" if model_ready else " İlk seferde yaklaşık 8 MB'lık el takip modelini internetten indireceğim."
    return (
        "Kamerayı açıp el hareketiyle pencere denetimini başlatmak istiyorum: başparmağı işaret parmağına kıstırıp sürükleyince "
        "öndeki pencere taşınır, orta parmakla boyutlanır, yüzük parmağıyla büyür, serçeyle küçülür. Kamera görüntüsü bilgisayardan "
        f"çıkmaz, Gemini'ye gönderilmez; 'kamerayı kapat' deyince biter.{note}"
    )


def _allowed() -> bool:
    """Ayarlar > İzinler'de kalıcı izin verildiyse sesli onay sorulmaz (izin güncellemelerde korunur)."""
    from jarvis.config import get_app_config_value

    return bool(get_app_config_value("hand_allowed", False))


def start_hand(webcam, ui=None, *, make_mover=None, ensure_model=None) -> str:
    """Kullanıcı onayı verildikten sonra çağrılır: modeli hazırlar, kamerayı açar, el takibini başlatır."""
    from jarvis import handtrack

    ensure_model = ensure_model or handtrack.ensure_model
    make_mover = make_mover or handtrack.HandMover
    say = getattr(ui, "hand_status", None) or (lambda text: None)
    if webcam.frame_hook is not None:
        return "El kontrolü zaten açık."
    say("el modeli hazırlanıyor…")
    error = ensure_model()
    if error:
        say("model indirilemedi")
        return error
    try:
        mover = make_mover(on_status=say)
    except Exception as exc:
        say("başlatılamadı")
        return f"El takibi başlatılamadı ({exc}). mediapipe kurulu olmayabilir."
    status = webcam.start()
    if status not in {"ok", "already_active"}:
        mover.close()
        say("kamera açılamadı")
        return "Kamera açılamadı."
    webcam.local_only = True
    webcam.frame_hook = mover.on_frame
    if ui:
        ui.set_webcam_active(True)
    say("hazır")
    return "El kontrolü açık. Başparmağı işaret parmağına kıstırıp sürükle (taşı), orta parmakla boyutlandır, yüzük parmağını 0,3 sn tut (büyüt), serçeyi tut (küçült)."


def stop_hand(webcam, ui=None) -> str:
    if webcam.frame_hook is None:
        return "El kontrolü zaten kapalı."
    webcam.stop()
    if ui:
        ui.set_webcam_active(False)
        getattr(ui, "hand_status", lambda text: None)("kapalı")
    return "El kontrolü ve kamera kapatıldı."


def hand_control(action: str, confirm_start: bool, webcam, ui=None, *, make_mover=None, model_ready=None, ensure_model=None) -> str:
    if webcam is None:
        return "Kamera bu oturumda kullanılamıyor."
    if action != "start":
        return stop_hand(webcam, ui)
    from jarvis import handtrack

    model_ready = model_ready or handtrack.model_ready
    if webcam.frame_hook is not None:
        return "El kontrolü zaten açık."
    if not confirm_start and not _allowed():
        return confirm.ask(KIND, (), _summary(model_ready()))
    if not _allowed():
        problem = confirm.check(KIND, ())
        if problem:
            return problem
    return start_hand(webcam, ui, make_mover=make_mover, ensure_model=ensure_model)
