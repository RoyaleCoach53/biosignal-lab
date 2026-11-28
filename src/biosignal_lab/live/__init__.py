"""Research streaming: simulated/device-clock data, bounded buffers and monitoring.

Physical acquisition boards and end-to-end timing have not been verified.
"""
from .core import Device, RingBuffer, SampleBlock, SimulatedDevice, StreamInfo
from .processing import LiveProcessor, LiveResult
from .recording import PlaybackDevice, load_recording, recording_bytes, save_recording
from .transport import SerialDevice, TCPDevice, UDPDevice, WebSocketDevice, encode_frame
from .clock import ClockAlignment
from .adapters import BrainFlowDevice, LSLDevice
from .session import AcquisitionSession
from .events import EventMarker
from .resources import process_memory_usage

__all__ = ["Device", "RingBuffer", "SampleBlock", "SimulatedDevice", "StreamInfo",
           "LiveProcessor", "LiveResult", "PlaybackDevice", "load_recording",
           "recording_bytes", "save_recording", "TCPDevice", "encode_frame", "ClockAlignment",
           "BrainFlowDevice", "LSLDevice", "SerialDevice", "UDPDevice", "WebSocketDevice", "AcquisitionSession",
           "EventMarker", "process_memory_usage"]
