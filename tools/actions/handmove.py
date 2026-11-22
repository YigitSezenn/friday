"""Kamera + el hareketiyle pencere taşıma. Açmadan önce kullanıcıdan sesli onay ister."""

from __future__ import annotations

from tools.actions import confirm

KIND = "hand_control"


def _summary(model_ready: bool) -> str:
    note = "" if model_ready else " İlk seferde yaklaşık 8 MB'lık el takip modelini internetten indireceğim."
    return (
        "Kamerayı açıp el hareketiyle pencere taşımayı başlatmak istiyorum: başparmak ve işaret parmağını birleştirip "
        "sürükleyince öndeki pencere taşınır, açınca bırakır. Kamera görüntüsü bilgisayardan çıkmaz, Gemini'ye gönderilmez; "
        f"'kamerayı kapat' deyince biter.{note}"
    )


def hand_control(action: str, confirm_start: bool, webcam, ui=None, *, make_mover=None, model_ready=None, ensure_model=None) -> str:
    if webcam is None:
        return "Kamera bu oturumda kullanılamıyor."
    if action != "start":
        if webcam.frame_hook is None:
            return "El kontrolü zaten kapalı."
        webcam.stop()
        if ui:
            ui.set_webcam_active(False)
        return "El kontrolü ve kamera kapatıldı."
    from jarvis import handtrack

    model_ready = model_ready or handtrack.model_ready
    ensure_model = ensure_model or handtrack.ensure_model
    make_mover = make_mover or handtrack.HandMover
    if webcam.frame_hook is not None:
        return "El kontrolü zaten açık."
    if not confirm_start:
        return confirm.ask(KIND, (), _summary(model_ready()))
    problem = confirm.check(KIND, ())
    if problem:
        return problem
    error = ensure_model()
    if error:
        return error
    try:
        mover = make_mover()
    except Exception as exc:
        return f"El takibi başlatılamadı ({exc}). mediapipe kurulu olmayabilir."
    status = webcam.start()
    if status not in {"ok", "already_active"}:
        mover.close()
        return "Kamera açılamadı."
    webcam.local_only = True
    webcam.frame_hook = mover.on_frame
    if ui:
        ui.set_webcam_active(True)
    return "El kontrolü açık. Başparmak ve işaret parmağını birleştirip sürükle; açınca pencere bırakılır."
