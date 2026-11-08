#!/usr/bin/env python3
"""One authenticated request to an explicitly selected local editor session."""

import argparse
import json
import re
import socket
import sys
import time
from pathlib import Path

API_VERSION = "editor-api/0.1"
MAX_REQUEST_BYTES = 1024 * 1024
MAX_FRAME_BYTES = MAX_REQUEST_BYTES + 256
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_INFO_BYTES = 16 * 1024
TIMEOUT_SECONDS = 30


class ClientError(Exception):
    """An error safe to report without discovery data or credentials."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ClientError("duplicate JSON keys are not allowed")
        result[key] = value
    return result


def reject_constant(_value):
    raise ClientError("non-finite JSON numbers are not allowed")


def parse_object(raw, label):
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ClientError(f"{label} must be a UTF-8 JSON object") from error
    if not isinstance(value, dict):
        raise ClientError(f"{label} must be a JSON object")
    return value


def read_bounded(stream, limit, label):
    raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ClientError(f"{label} exceeds its byte budget")
    return raw


def read_file(path, limit, label):
    try:
        with Path(path).open("rb") as stream:
            return read_bounded(stream, limit, label)
    except OSError as error:
        raise ClientError(f"cannot read {label}") from error


def discovery(path):
    info = parse_object(read_file(path, MAX_INFO_BYTES, "API info"), "API info")
    if info.get("apiVersion") != API_VERSION:
        raise ClientError("unsupported discovery apiVersion")
    for key in ("address", "token", "instanceId", "exportRoot"):
        if not isinstance(info.get(key), str) or not info[key]:
            raise ClientError("API info is missing required string fields")
    match = re.fullmatch(r"127\.0\.0\.1:([1-9][0-9]{0,4})", info["address"])
    if not match or int(match[1]) > 65535:
        raise ClientError("API address must be exactly 127.0.0.1:port")
    if not re.fullmatch(r"[0-9a-f]{64}", info["token"]):
        raise ClientError("invalid local credential format")
    return info, ("127.0.0.1", int(match[1]))


def load_request(path):
    raw = (
        read_file(path, MAX_REQUEST_BYTES, "request")
        if path is not None
        else read_bounded(sys.stdin.buffer, MAX_REQUEST_BYTES, "request")
    )
    request = parse_object(raw, "request")
    if set(request) - {"apiVersion", "id", "method", "params", "sessionId"}:
        raise ClientError("request contains unsupported top-level fields")
    if request.get("apiVersion") != API_VERSION:
        raise ClientError("request apiVersion must be editor-api/0.1")
    encode_json(request)
    for key, limit in (("id", 128), ("method", 64)):
        value = request.get(key)
        if not isinstance(value, str) or not 1 <= len(value.encode("utf-8")) <= limit:
            raise ClientError(f"request {key} has an invalid byte length")
    if not isinstance(request.get("params", {}), dict):
        raise ClientError("request params must be an object")
    request.setdefault("params", {})
    return request


def make_frame(info, request, selected_session):
    request_session = request.pop("sessionId", None)
    for session in (selected_session, request_session):
        if session is not None and (not isinstance(session, str) or not session):
            raise ClientError("sessionId must be a nonempty string")
    if selected_session is not None and request_session is not None:
        if selected_session != request_session:
            raise ClientError("--session conflicts with request sessionId")
    session = selected_session if selected_session is not None else request_session
    if request["method"] != "editor.capabilities" and session is None:
        raise ClientError("explicit --session or request sessionId is required")
    payload = encode_json(request)
    if len(payload) > MAX_REQUEST_BYTES:
        raise ClientError("request exceeds 1 MiB")
    envelope = {"token": info["token"], "request": request}
    if session is not None:
        envelope["sessionId"] = session
    frame = encode_json(envelope) + b"\n"
    if len(frame) > MAX_FRAME_BYTES:
        raise ClientError("request frame exceeds 1 MiB plus envelope budget")
    return frame


def encode_json(value):
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ClientError("JSON cannot be encoded within supported limits") from error


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise ClientError("request exceeded the 30 second deadline; it was not retried")
    return seconds


def receive_frame(connection, deadline):
    data = bytearray()
    while True:
        connection.settimeout(remaining(deadline))
        chunk = connection.recv(min(65536, MAX_RESPONSE_BYTES + 1 - len(data)))
        if not chunk:
            raise ClientError("editor closed the connection before a complete response")
        data.extend(chunk)
        newline = data.find(b"\n")
        if newline >= 0:
            if newline > MAX_RESPONSE_BYTES or data[newline + 1 :].strip():
                raise ClientError("invalid or oversized response frame")
            return bytes(data[:newline])
        if len(data) > MAX_RESPONSE_BYTES:
            raise ClientError("response exceeds 32 MiB")


def exchange(address, frame):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        with socket.create_connection(address, timeout=remaining(deadline)) as connection:
            connection.settimeout(remaining(deadline))
            connection.sendall(frame)
            return receive_frame(connection, deadline)
    except TimeoutError as error:
        raise ClientError("request timed out; it was not retried") from error
    except OSError as error:
        raise ClientError("local editor connection failed; it was not retried") from error


def check_response(raw, request):
    response = parse_object(raw, "response")
    if response.get("apiVersion") != API_VERSION:
        raise ClientError("unsupported response apiVersion")
    has_result, has_error = "result" in response, "error" in response
    if has_result == has_error:
        raise ClientError("response must contain exactly one result or error")
    if response.get("id") != request["id"]:
        if not (has_error and response.get("id") == ""):
            raise ClientError("response request id does not match")
    if has_error and not isinstance(response["error"], dict):
        raise ClientError("response error must be an object")
    return response


def write_response(response, token):
    encode_json(response)
    text = json.dumps(response, ensure_ascii=False, allow_nan=False, indent=2)
    # Never echo the credential, even if an unexpected server response contains it.
    sys.stdout.write(text.replace(token, "[REDACTED]") + "\n")


def exit_status(response, method):
    if "error" in response:
        return 1
    result = response["result"]
    if method == "job.status" and isinstance(result, dict):
        if result.get("status") in ("failed", "cancelled"):
            return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--info", required=True, help="private local discovery JSON path")
    parser.add_argument("--request", help="UTF-8 request JSON file; otherwise read stdin")
    parser.add_argument("--session", help="explicit document sessionId; never chosen automatically")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    try:
        info, address = discovery(args.info)
        request = load_request(args.request)
        frame = make_frame(info, request, args.session)
        response = check_response(exchange(address, frame), request)
        write_response(response, info["token"])
        return exit_status(response, request["method"])
    except ClientError as error:
        sys.stderr.write(f"editor-api: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
