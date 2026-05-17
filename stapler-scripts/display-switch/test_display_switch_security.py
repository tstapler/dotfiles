import os
import stat
import subprocess
import pytest
import getpass
from unittest.mock import patch, MagicMock
import display_switch

@pytest.fixture
def mock_env(tmp_path):
    # Setup a clean environment for testing
    state_file = tmp_path / "monitor_state.sh"
    log_file = tmp_path / "display_switch.log"
    with patch('display_switch.STATE_FILE', str(state_file)), \
         patch('display_switch.LOG_FILE', str(log_file)):
        yield state_file, log_file

def test_secure_path_generation():
    user = getpass.getuser()
    with patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1000"}):
        with patch('os.path.isdir', return_value=True), patch('os.access', return_value=True):
            path = display_switch._get_secure_path("test.sh")
            assert path == f"/run/user/1000/display-switch-{user}-test.sh"

    with patch.dict(os.environ, {}, clear=True):
        path = display_switch._get_secure_path("test.sh")
        assert path == f"/tmp/display-switch-{user}-test.sh"

@patch('display_switch.get_current_state')
@patch('subprocess.run')
def test_save_state_secure_creation(mock_run, mock_get_state, mock_env):
    state_file, _ = mock_env
    mock_get_state.return_value = [{
        "name": "HDMI-0", "primary": True, "active": True,
        "pos": "0x0", "rotation": "normal", "active_mode": "1920x1080", "rate": "60.00"
    }]

    display_switch.save_state()

    assert state_file.exists()
    st = os.stat(state_file)
    # Check permissions are 0o600 (rw-------)
    assert stat.S_IMODE(st.st_mode) == 0o600

    with open(state_file, 'r') as f:
        content = f.read()
        assert "#!/bin/bash" in content
        assert "xrandr --output HDMI-0 --primary --mode 1920x1080 --rate 60.00 --pos 0x0 --rotate normal" in content

@patch('subprocess.run')
def test_restore_state_secure_execution(mock_run, mock_env):
    state_file, _ = mock_env
    state_file.write_text("#!/bin/bash\nxrandr --output HDMI-0 --auto")
    os.chmod(state_file, 0o600)

    display_switch.restore_state()

    # Ensure it was called with bash and NO shell=True
    mock_run.assert_called_once_with(["/bin/bash", str(state_file)], check=True)
    assert not state_file.exists()

@patch('subprocess.run')
def test_restore_state_rejects_insecure_permissions(mock_run, mock_env):
    state_file, _ = mock_env
    state_file.write_text("#!/bin/bash\nxrandr --output HDMI-0 --auto")
    # Set insecure permissions (e.g., world-readable)
    os.chmod(state_file, 0o644)

    display_switch.restore_state()

    mock_run.assert_not_called()
    assert state_file.exists()

@patch('display_switch.get_current_state')
def test_save_state_command_injection_prevention(mock_get_state, mock_env):
    state_file, _ = mock_env
    # Malicious monitor name
    mock_get_state.return_value = [{
        "name": "HDMI-0; rm -rf /", "primary": False, "active": True,
        "pos": "0x0", "rotation": "normal", "active_mode": "1920x1080", "rate": "60.00"
    }]

    display_switch.save_state()

    with open(state_file, 'r') as f:
        content = f.read()
        # The malicious name should be quoted as a single argument
        assert "xrandr --output 'HDMI-0; rm -rf /' --mode 1920x1080" in content
