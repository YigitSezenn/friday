"""Windows Voice Capture DSP (CLSID_CWMAudioAEC).

Kaynak kipinde mikrofonu ve hoparlör geri döngüsünü kendisi açar. Çıktı 16 kHz mono
16 bit; hoparlörden gelen ses silinir ve akustik yankı bastırma (AES) iki kez uygulanır.
DSP yoksa çağıran düz mikrofona döner.
"""

from __future__ import annotations

import ctypes
import queue
import threading
import uuid
from ctypes import wintypes

MIC_RATE = 16000
CHUNK = 1024
_INCOMPLETE = 0x01000000
_PID_SYSTEM_MODE = 2
_PID_DEVICE_INDEXES = 4
_PID_FEATURE_MODE = 5
_PID_AES = 10
_PID_MIC_GAIN_BOUNDER = 21
_VT_I4 = 3
_VT_BOOL = 11
_CLSCTX = 1
_RENDER = 0
_CAPTURE = 1
_CONSOLE = 0
_ACTIVE = 1

_CLSID_AEC = "745057C7-F353-4F2D-A7EE-58434477730E"
_IID_MEDIA_OBJECT = "D8AD0F58-5494-4102-97C5-EC798E59BCF4"
_IID_PROPERTY_STORE = "886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"
_CLSID_ENUMERATOR = "BCDE0395-E52F-467C-8E3D-C4579291692E"
_IID_ENUMERATOR = "A95664D2-9614-4F35-A746-DE8DB63617E6"
_FMTID_AEC = "6F52C567-0360-4BD2-9617-CCBF1421C939"
_MEDIATYPE_AUDIO = "73647561-0000-0010-8000-00AA00389B71"
_SUBTYPE_PCM = "00000001-0000-0010-8000-00AA00389B71"
_FORMAT_WAVE = "05589F81-C356-11CE-BF01-00AA0055595A"


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _WaveFormat(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class _MediaType(ctypes.Structure):
    _fields_ = [
        ("majortype", _GUID),
        ("subtype", _GUID),
        ("bFixedSizeSamples", wintypes.BOOL),
        ("bTemporalCompression", wintypes.BOOL),
        ("lSampleSize", wintypes.ULONG),
        ("formattype", _GUID),
        ("pUnk", ctypes.c_void_p),
        ("cbFormat", wintypes.ULONG),
        ("pbFormat", ctypes.c_void_p),
    ]


class _OutputBuffer(ctypes.Structure):
    _fields_ = [
        ("pBuffer", ctypes.c_void_p),
        ("dwStatus", wintypes.DWORD),
        ("rtTimestamp", ctypes.c_longlong),
        ("rtTimelength", ctypes.c_longlong),
    ]


class _PropKey(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", wintypes.DWORD)]


class _PropVariant(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("r1", ctypes.c_ushort),
        ("r2", ctypes.c_ushort),
        ("r3", ctypes.c_ushort),
        ("value", ctypes.c_ulonglong),
        ("extra", ctypes.c_ulonglong),
    ]


def _guid(text: str) -> _GUID:
    value = _GUID()
    ctypes.memmove(ctypes.byref(value), uuid.UUID(text).bytes_le, 16)
    return value


def _method(obj, index: int, *argtypes):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0]
    function = ctypes.cast(
        ctypes.cast(table, ctypes.POINTER(ctypes.c_void_p))[index],
        ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes),
    )

    def call(*args):
        return function(obj, *args)

    return call


def _release(obj) -> None:
    if obj:
        _method(obj, 2)()


def _hr(code: int) -> str:
    return f"0x{code & 0xFFFFFFFF:08X}"


class _Buffer:
    def __init__(self, size: int) -> None:
        self.size = size
        self.length = 0
        self.data = ctypes.create_string_buffer(size)
        query = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(self._query)
        addref = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(lambda _this: 1)
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(lambda _this: 1)
        setlen = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.DWORD)(self._setlen)
        getmax = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD))(self._getmax)
        getbuf = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)
        )(self._getbuf)
        self._vt = (ctypes.c_void_p * 6)(
            ctypes.cast(query, ctypes.c_void_p),
            ctypes.cast(addref, ctypes.c_void_p),
            ctypes.cast(release, ctypes.c_void_p),
            ctypes.cast(setlen, ctypes.c_void_p),
            ctypes.cast(getmax, ctypes.c_void_p),
            ctypes.cast(getbuf, ctypes.c_void_p),
        )
        self._obj = ctypes.c_void_p(ctypes.addressof(self._vt))
        self.ptr = ctypes.cast(ctypes.pointer(self._obj), ctypes.c_void_p)
        self._keep = (query, addref, release, setlen, getmax, getbuf)

    def _query(self, _this, _iid, out):
        out[0] = self.ptr
        return 0

    def _setlen(self, _this, length):
        self.length = min(int(length), self.size)
        return 0

    def _getmax(self, _this, out):
        out[0] = self.size
        return 0

    def _getbuf(self, _this, data, length):
        if data:
            data[0] = ctypes.addressof(self.data)
        if length:
            length[0] = self.length
        return 0

    def take(self) -> bytes:
        size = min(self.length, self.size)
        self.length = 0
        return self.data.raw[:size]


def _device_index(enum, flow: int, wanted: str) -> int:
    collection = ctypes.c_void_p()
    code = _method(enum, 3, ctypes.c_int, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p))(flow, _ACTIVE, ctypes.byref(collection))
    if code < 0 or not collection.value:
        return 0
    try:
        count = wintypes.UINT()
        _method(collection, 3, ctypes.POINTER(wintypes.UINT))(ctypes.byref(count))
        for index in range(int(count.value)):
            device = ctypes.c_void_p()
            if _method(collection, 4, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))(index, ctypes.byref(device)) < 0:
                continue
            try:
                raw = ctypes.c_void_p()
                if _method(device, 5, ctypes.POINTER(ctypes.c_void_p))(ctypes.byref(raw)) < 0:
                    continue
                ident = ctypes.wstring_at(raw) if raw.value else ""
                ctypes.windll.ole32.CoTaskMemFree(raw)
                if wanted and ident == wanted:
                    return index
            finally:
                _release(device)
        return 0
    finally:
        _release(collection)


def _default_id(enum, flow: int) -> str:
    device = ctypes.c_void_p()
    code = _method(enum, 4, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(
        flow, _CONSOLE, ctypes.byref(device)
    )
    if code < 0 or not device.value:
        return ""
    try:
        raw = ctypes.c_void_p()
        if _method(device, 5, ctypes.POINTER(ctypes.c_void_p))(ctypes.byref(raw)) < 0:
            return ""
        ident = ctypes.wstring_at(raw) if raw.value else ""
        ctypes.windll.ole32.CoTaskMemFree(raw)
        return ident
    finally:
        _release(device)


class _Dsp:
    def __init__(self) -> None:
        self.dmo = ctypes.c_void_p()
        self.store = ctypes.c_void_p()
        self.buffer = _Buffer(MIC_RATE * 2)
        ole32 = ctypes.windll.ole32
        ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(_GUID), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)
        ]
        ole32.CoCreateInstance.restype = ctypes.c_long
        code = ole32.CoCreateInstance(
            ctypes.byref(_guid(_CLSID_AEC)), None, _CLSCTX, ctypes.byref(_guid(_IID_MEDIA_OBJECT)), ctypes.byref(self.dmo)
        )
        if code < 0 or not self.dmo.value:
            raise OSError(f"Voice Capture DSP yok ({_hr(code)})")
        code = _method(self.dmo, 0, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(
            ctypes.byref(_guid(_IID_PROPERTY_STORE)), ctypes.byref(self.store)
        )
        if code < 0 or not self.store.value:
            raise OSError(f"DSP ayarları açılamadı ({_hr(code)})")
        self._set(_PID_SYSTEM_MODE, _VT_I4, 0)
        self._set(_PID_MIC_GAIN_BOUNDER, _VT_BOOL, 0)
        self._set(_PID_FEATURE_MODE, _VT_BOOL, 1)
        self._set(_PID_AES, _VT_I4, 2)
        enum = ctypes.c_void_p()
        code = ole32.CoCreateInstance(
            ctypes.byref(_guid(_CLSID_ENUMERATOR)), None, _CLSCTX, ctypes.byref(_guid(_IID_ENUMERATOR)), ctypes.byref(enum)
        )
        mic = spk = 0
        if code >= 0 and enum.value:
            try:
                mic = _device_index(enum, _CAPTURE, _default_id(enum, _CAPTURE))
                spk = _device_index(enum, _RENDER, _default_id(enum, _RENDER))
            finally:
                _release(enum)
        packed = ((spk & 0xFFFF) << 16) | (mic & 0xFFFF)
        self._set(_PID_DEVICE_INDEXES, _VT_I4, packed)
        fmt = _WaveFormat(1, 1, MIC_RATE, MIC_RATE * 2, 2, 16, 0)
        kind = _MediaType()
        kind.majortype = _guid(_MEDIATYPE_AUDIO)
        kind.subtype = _guid(_SUBTYPE_PCM)
        kind.bFixedSizeSamples = 1
        kind.lSampleSize = 2
        kind.formattype = _guid(_FORMAT_WAVE)
        kind.cbFormat = ctypes.sizeof(fmt)
        kind.pbFormat = ctypes.cast(ctypes.pointer(fmt), ctypes.c_void_p)
        code = _method(self.dmo, 9, wintypes.DWORD, ctypes.POINTER(_MediaType), wintypes.DWORD)(0, ctypes.byref(kind), 0)
        if code < 0:
            raise OSError(f"DSP çıktı biçimi kabul edilmedi ({_hr(code)})")
        code = _method(self.dmo, 18)()
        if code < 0:
            raise OSError(f"DSP mikrofonu açamadı ({_hr(code)})")
        self._fmt = fmt

    def _set(self, pid: int, vt: int, value: int, required: bool = True) -> None:
        var = _PropVariant()
        var.vt = vt
        var.value = 0xFFFF if vt == _VT_BOOL and value else (int(value) & 0xFFFFFFFF)
        key = _PropKey(_guid(_FMTID_AEC), pid)
        code = _method(self.store, 6, ctypes.POINTER(_PropKey), ctypes.POINTER(_PropVariant))(
            ctypes.byref(key), ctypes.byref(var)
        )
        if code < 0 and required:
            raise OSError(f"DSP ayarı {pid} kabul edilmedi ({_hr(code)})")

    def read(self) -> bytes:
        process = _method(
            self.dmo,
            22,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(_OutputBuffer),
            ctypes.POINTER(wintypes.DWORD),
        )
        out = bytearray()
        for _ in range(8):
            entry = _OutputBuffer()
            entry.pBuffer = self.buffer.ptr
            status = wintypes.DWORD()
            code = process(0, 1, ctypes.byref(entry), ctypes.byref(status))
            if code < 0:
                raise OSError(f"DSP okunamadı ({_hr(code)})")
            out.extend(self.buffer.take())
            if not (entry.dwStatus & _INCOMPLETE):
                break
        return bytes(out)

    def close(self) -> None:
        _release(self.dmo)
        _release(self.store)
        self.dmo = ctypes.c_void_p()
        self.store = ctypes.c_void_p()


class DspMic:
    """Yankısı ve gürültüsü silinmiş mikrofon. read(), pyaudio ile aynı parça boyutunu verir."""

    echo_cancelled = True
    path = "yankı engellemeli"

    def __init__(self) -> None:
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=24)
        self._halt = threading.Event()
        self._ready = threading.Event()
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="friday-aec", daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            self.close()
            raise OSError(self._error or "yankı engelleme yanıt vermedi")

    def _run(self) -> None:
        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        ole32.CoInitializeEx.restype = ctypes.c_long
        started = ole32.CoInitializeEx(None, 0) >= 0
        dsp = None
        try:
            dsp = _Dsp()
            self._ready.set()
            pending = bytearray()
            while not self._halt.is_set():
                pending.extend(dsp.read())
                while len(pending) >= CHUNK * 2:
                    piece = bytes(pending[: CHUNK * 2])
                    del pending[: CHUNK * 2]
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                        except queue.Empty:
                            pass
                    self._queue.put(piece)
                if not pending:
                    self._halt.wait(0.01)
        except Exception as exc:
            self._error = exc
            self._ready.set()
        finally:
            if dsp is not None:
                dsp.close()
            if started:
                ole32.CoUninitialize()

    def read(self, _frames: int = CHUNK, exception_on_overflow: bool = False) -> bytes:
        try:
            return self._queue.get(timeout=2)
        except queue.Empty:
            return b"\x00" * (CHUNK * 2)

    def close(self) -> None:
        self._halt.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)


def open_dsp_mic() -> DspMic | None:
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return None
    try:
        return DspMic()
    except (OSError, AttributeError):
        return None
