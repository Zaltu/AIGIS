"""
Module for SSH utils and the connection manager singleton.
"""
import paramiko
import scp

from utils import path_utils  #pylint: disable=no-name-in-module
from utils.log_utils import LOG  #pylint: disable=no-name-in-module
from utils.exc_utils import PluginLoadError  #pylint: disable=no-name-in-module

PORT = 22

CHECK_PROXINATOR_CMD = f"test -f {path_utils.REMOTE_PROXI_PATH} && echo \"true\""


class SSHClient:
    """
    Helper class to establish SSH connections with remote hosts for internal-remote plugins.
    Class attribute `user_password` should be set before any connection attempts are made.

    Connections are made using the user "aigis", and a password set in the aigis config file.
    """
    user_login = None
    user_password = None
    def __init__(self):
        self.client = None

    def connect(self, host):
        """
        Create a connection to a remote host, if one does not already exist.
        Also ensures the host is at least basically valid, which means having python3.7 installed.

        :param str host: hostname/IP to connect to

        :raises NoRemotePythonException: if python3.7 is not installed on the host.
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=host,
            port=PORT,
            username=SSHClient.user_login,
            password=SSHClient.user_password,
            look_for_keys=False,
            allow_agent=False
        )

        try:
            self._exec("which python3.7")
        except RemoteErrException:
            raise NoRemotePythonException("%s has no python3.7 installed." % host)

    def send_path(self, local_root, remote_root):
        """
        Send the plugin files over SSH to the remote host.

        :param str local_root: local plugin root
        :param str remote_root: remote plugin root
        """
        self._scp_file(local_root, remote_root)

    def ensure_proxinator(self):
        """
        Make sure the remote host has the proxinator.
        If the remote host has no proxinator, SCP it over.
        """
        if self.has_proxinator():
            return
        self._scp_file(path_utils.PROXI_PATH, path_utils.REMOTE_PROXI_PATH)

    def has_proxinator(self):
        """
        Check if the remote host already has the proxinator files.
        This can happen if more than one plugin is set to run on the same remote host, which is expected.

        :returns: if the remote host has the proxinator
        :rtype: bool
        """
        return bool(self._exec(CHECK_PROXINATOR_CMD))

    def ensure_remote_path_exists(self, path):
        """
        Ensure that a remote path exists.

        :param str path: remote path to check
        """
        try:
            self._exec("ls %s" % path)
        except RemoteErrException:
            self._exec("python3.7 -c \"with open('%s', 'w+') as f: pass\"" % path)

    def close(self, host, plugin_name):
        """
        Close a connection.

        :param str host: host to close connection to.
        :param str plugin_name: plugin who's connection to close
        """
        try:
            self.client.close()
        except AttributeError:
            LOG.warning("Attempted to close %s connection to %s, but it doesn't exist...", plugin_name, host)

    def _exec(self, script, linuxLineEndings=True, decodeBinaryStrings=True):
        """
        Execute a bash/shell command over an SSH connection. `connect` must be called beforehand.

        :param str script: script to execute remotely
        :param bool linuxLineEndings: convert received line endings from windows to linux format, default True
        :param bool decodeBinaryStrings: decode returned binary string to normal string, default True

        :raises RemoteErrException: if the remote script wrote anything to stderr
        :returns: stdout of the script that was run remotely
        :rtype: str
        """
        _, stdout, stderr = self.client.exec_command(script)  # _ = stdin
        output = stdout.read()
        errorOutput = stderr.read()
        if linuxLineEndings:
            output = output.replace(b"\r\n", b"\n")
        if decodeBinaryStrings:
            output = output.decode()
            errorOutput = errorOutput.decode()
        if errorOutput:
            raise RemoteErrException(errorOutput)
        return output

    def _scp_file(self, source, dest):
        """
        Copy a file or directory to the remote host using SCP.

        :param str source: local path to source
        :param str dest: remote path to destination

        :raises RemoteErrException: if the SCP client raised an error
        """
        scp_client = scp.SCPClient(self.client.get_transport())
        try:
            scp_client.put(
                source,
                recursive=True,
                remote_path=dest
            )
        except scp.SCPException as e:
            raise RemoteErrException(str(e))
        finally:
            scp_client.close()


class RemoteErrException(PluginLoadError):
    """
    A remote process printed to stderr.
    """

class NoRemotePythonException(PluginLoadError):
    """
    A remote host has no "python3.7" binary.
    """
