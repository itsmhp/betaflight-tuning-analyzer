"""
Betaflight Blackbox Flight Data Parser.

Processes CSV output from blackbox_decode tool and provides
structured access to flight data for analysis.
"""
import csv
import io
import subprocess
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..config import BLACKBOX_DECODE_PATH, TOOLS_DIR


@dataclass
class FlightData:
    """Structured flight data from a blackbox log."""
    # Time series arrays (numpy)
    time_us: Optional[np.ndarray] = None  # timestamps in microseconds
    loop_iteration: Optional[np.ndarray] = None

    # Gyro data (degrees/sec)
    gyro_roll: Optional[np.ndarray] = None
    gyro_pitch: Optional[np.ndarray] = None
    gyro_yaw: Optional[np.ndarray] = None

    # Unfiltered gyro (if available)
    gyro_unfilt_roll: Optional[np.ndarray] = None
    gyro_unfilt_pitch: Optional[np.ndarray] = None
    gyro_unfilt_yaw: Optional[np.ndarray] = None

    # PID outputs
    pid_p_roll: Optional[np.ndarray] = None
    pid_p_pitch: Optional[np.ndarray] = None
    pid_p_yaw: Optional[np.ndarray] = None
    pid_i_roll: Optional[np.ndarray] = None
    pid_i_pitch: Optional[np.ndarray] = None
    pid_i_yaw: Optional[np.ndarray] = None
    pid_d_roll: Optional[np.ndarray] = None
    pid_d_pitch: Optional[np.ndarray] = None
    pid_d_yaw: Optional[np.ndarray] = None
    pid_f_roll: Optional[np.ndarray] = None
    pid_f_pitch: Optional[np.ndarray] = None
    pid_f_yaw: Optional[np.ndarray] = None

    # RC commands
    rc_command_roll: Optional[np.ndarray] = None
    rc_command_pitch: Optional[np.ndarray] = None
    rc_command_yaw: Optional[np.ndarray] = None
    rc_command_throttle: Optional[np.ndarray] = None

    # Setpoints
    setpoint_roll: Optional[np.ndarray] = None
    setpoint_pitch: Optional[np.ndarray] = None
    setpoint_yaw: Optional[np.ndarray] = None
    setpoint_throttle: Optional[np.ndarray] = None

    # Motor outputs
    motor: List[Optional[np.ndarray]] = field(default_factory=lambda: [None, None, None, None])

    # eRPM
    erpm: List[Optional[np.ndarray]] = field(default_factory=lambda: [None, None, None, None])

    # Battery
    vbat: Optional[np.ndarray] = None
    amperage: Optional[np.ndarray] = None

    # Accelerometer
    acc_x: Optional[np.ndarray] = None
    acc_y: Optional[np.ndarray] = None
    acc_z: Optional[np.ndarray] = None

    # Debug
    debug: List[Optional[np.ndarray]] = field(default_factory=lambda: [None] * 8)

    # RSSI
    rssi: Optional[np.ndarray] = None

    # Energy
    energy_mah: Optional[np.ndarray] = None

    # Metadata
    sample_count: int = 0
    duration_seconds: float = 0.0
    sample_rate_hz: float = 0.0
    available_fields: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Indexed-access properties (for analyzers that use axis indices)
    # ------------------------------------------------------------------

    @property
    def gyro_filtered(self) -> List[Optional[np.ndarray]]:
        """Filtered gyro [roll, pitch, yaw] – same data as gyro_roll/pitch/yaw."""
        return [self.gyro_roll, self.gyro_pitch, self.gyro_yaw]

    @property
    def gyro_unfiltered(self) -> List[Optional[np.ndarray]]:
        """Unfiltered gyro [roll, pitch, yaw]."""
        return [self.gyro_unfilt_roll, self.gyro_unfilt_pitch, self.gyro_unfilt_yaw]

    @property
    def setpoint(self) -> List[Optional[np.ndarray]]:
        """Setpoint [roll, pitch, yaw, throttle]."""
        return [self.setpoint_roll, self.setpoint_pitch, self.setpoint_yaw, self.setpoint_throttle]

    @property
    def rc_command(self) -> List[Optional[np.ndarray]]:
        """RC command [roll, pitch, yaw, throttle]."""
        return [self.rc_command_roll, self.rc_command_pitch, self.rc_command_yaw, self.rc_command_throttle]

    @property
    def pid_p(self) -> List[Optional[np.ndarray]]:
        """PID P-term [roll, pitch, yaw]."""
        return [self.pid_p_roll, self.pid_p_pitch, self.pid_p_yaw]

    @property
    def pid_i(self) -> List[Optional[np.ndarray]]:
        """PID I-term [roll, pitch, yaw]."""
        return [self.pid_i_roll, self.pid_i_pitch, self.pid_i_yaw]

    @property
    def pid_d(self) -> List[Optional[np.ndarray]]:
        """PID D-term [roll, pitch, yaw]."""
        return [self.pid_d_roll, self.pid_d_pitch, self.pid_d_yaw]

    @property
    def pid_f(self) -> List[Optional[np.ndarray]]:
        """PID F-term (feedforward) [roll, pitch, yaw]."""
        return [self.pid_f_roll, self.pid_f_pitch, self.pid_f_yaw]


class BBLDataParser:
    """Parse blackbox flight data using blackbox_decode tool."""

    # Column name mapping from CSV to FlightData attributes
    COLUMN_MAP = {
        "loopIteration": "loop_iteration",
        "time (us)": "time_us",
        "time": "time_us",
        "axisP[0]": "pid_p_roll",
        "axisP[1]": "pid_p_pitch",
        "axisP[2]": "pid_p_yaw",
        "axisI[0]": "pid_i_roll",
        "axisI[1]": "pid_i_pitch",
        "axisI[2]": "pid_i_yaw",
        "axisD[0]": "pid_d_roll",
        "axisD[1]": "pid_d_pitch",
        "axisD[2]": "pid_d_yaw",  # Note: usually 0 for yaw
        "axisF[0]": "pid_f_roll",
        "axisF[1]": "pid_f_pitch",
        "axisF[2]": "pid_f_yaw",
        "rcCommand[0]": "rc_command_roll",
        "rcCommand[1]": "rc_command_pitch",
        "rcCommand[2]": "rc_command_yaw",
        "rcCommand[3]": "rc_command_throttle",
        "setpoint[0]": "setpoint_roll",
        "setpoint[1]": "setpoint_pitch",
        "setpoint[2]": "setpoint_yaw",
        "setpoint[3]": "setpoint_throttle",
        "vbatLatest (V)": "vbat",
        "vbatLatest": "vbat",
        "amperageLatest (A)": "amperage",
        "amperageLatest": "amperage",
        "rssi": "rssi",
        "gyroADC[0]": "gyro_roll",
        "gyroADC[1]": "gyro_pitch",
        "gyroADC[2]": "gyro_yaw",
        "gyroUnfilt[0]": "gyro_unfilt_roll",
        "gyroUnfilt[1]": "gyro_unfilt_pitch",
        "gyroUnfilt[2]": "gyro_unfilt_yaw",
        "accSmooth[0]": "acc_x",
        "accSmooth[1]": "acc_y",
        "accSmooth[2]": "acc_z",
        # Energy
        "energyCumulative (mAh)": "energy_mah",
        "energyCumulative": "energy_mah",
    }

    def decode_bbl_file(self, bbl_path: str, log_index: int = 0) -> Optional[str]:
        """
        Use blackbox_decode to convert BBL to CSV.

        Args:
            bbl_path: Path to .bbl file
            log_index: Which log to decode (0-based) if multiple logs in file

        Returns:
            Path to generated CSV file, or None if decode failed
        """
        if not BLACKBOX_DECODE_PATH.exists():
            return None

        bbl_path = Path(bbl_path)
        if not bbl_path.exists():
            return None

        try:
            # Run blackbox_decode
            cmd = [
                str(BLACKBOX_DECODE_PATH),
                str(bbl_path),
                "--index", str(log_index + 1),  # 1-based index
                "--merge-gps",
                "--stdout",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(TOOLS_DIR),
            )

            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                # Try without --stdout, check for output file
                cmd_file = [
                    str(BLACKBOX_DECODE_PATH),
                    str(bbl_path),
                    "--index", str(log_index + 1),
                ]
                result = subprocess.run(
                    cmd_file,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                # Look for generated CSV
                csv_name = bbl_path.stem + f".{log_index + 1:02d}.csv"
                csv_path = bbl_path.parent / csv_name
                if csv_path.exists():
                    with open(csv_path, "r") as f:
                        return f.read()

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            print(f"blackbox_decode error: {e}")

        return None

    def parse_csv(self, csv_text: str) -> FlightData:
        """Parse CSV text (from blackbox_decode output) into FlightData."""
        data = FlightData()

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            return data

        data.available_fields = list(reader.fieldnames)

        # Read all rows into columns
        columns: Dict[str, List[float]] = {name: [] for name in reader.fieldnames}

        for row in reader:
            for key, val in row.items():
                try:
                    columns[key].append(float(val))
                except (ValueError, TypeError):
                    columns[key].append(0.0)

        if not columns or not any(columns.values()):
            return data

        # Convert to numpy arrays and map to FlightData fields
        for csv_col, attr_name in self.COLUMN_MAP.items():
            if csv_col in columns and columns[csv_col]:
                arr = np.array(columns[csv_col], dtype=np.float64)
                setattr(data, attr_name, arr)

        # Handle motor columns
        for i in range(4):
            col_name = f"motor[{i}]"
            if col_name in columns and columns[col_name]:
                data.motor[i] = np.array(columns[col_name], dtype=np.float64)

        # Handle eRPM columns
        for i in range(4):
            col_name = f"eRPM[{i}]"
            if col_name in columns and columns[col_name]:
                data.erpm[i] = np.array(columns[col_name], dtype=np.float64)

        # Handle debug columns
        for i in range(8):
            col_name = f"debug[{i}]"
            if col_name in columns and columns[col_name]:
                data.debug[i] = np.array(columns[col_name], dtype=np.float64)

        # Calculate metadata
        if data.time_us is not None and len(data.time_us) > 1:
            data.sample_count = len(data.time_us)
            data.duration_seconds = (data.time_us[-1] - data.time_us[0]) / 1_000_000
            if data.duration_seconds > 0:
                data.sample_rate_hz = data.sample_count / data.duration_seconds

        return data

    def parse_bbl_file(self, bbl_path: str, log_index: int = 0) -> Optional[FlightData]:
        """
        Full pipeline: decode BBL file and parse into FlightData.

        Args:
            bbl_path: Path to .bbl file
            log_index: Which log to decode (0-based)

        Returns:
            FlightData or None if decoding failed
        """
        csv_text = self.decode_bbl_file(bbl_path, log_index)
        if csv_text:
            return self.parse_csv(csv_text)
        return None

    @staticmethod
    def check_decoder_available() -> bool:
        """Check if blackbox_decode binary is available."""
        return BLACKBOX_DECODE_PATH.exists()

    @staticmethod
    def get_decoder_download_url() -> str:
        """Return download URL for blackbox_decode."""
        return "https://github.com/betaflight/blackbox-tools/releases"
