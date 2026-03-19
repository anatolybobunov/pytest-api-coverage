"""Integration tests for the pytest-api-coverage plugin using pytester."""

import textwrap


def test_plugin_active_with_coverage_spec(pytester):
    """Plugin activates and records requests when --coverage-spec is provided."""
    spec_file = pytester.makefile(
        ".yaml",
        spec=textwrap.dedent("""\
            openapi: "3.0.0"
            info:
              title: Test API
              version: "1.0"
            paths:
              /get:
                get:
                  responses:
                    "200":
                      description: OK
        """),
    )

    pytester.makepyfile(
        textwrap.dedent("""\
            import requests
            import responses as resp

            @resp.activate
            def test_get():
                resp.add(resp.GET, "https://httpbin.org/get", json={}, status=200)
                r = requests.get("https://httpbin.org/get")
                assert r.status_code == 200
        """)
    )

    result = pytester.runpytest(
        f"--coverage-spec={spec_file}",
        "--coverage-url-filter=httpbin.org",
        "--coverage-format=json",
    )
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*API Coverage Summary*"])


def test_plugin_inactive_without_flags(pytester):
    """Plugin does not produce output when no coverage flags are given."""
    pytester.makepyfile(
        textwrap.dedent("""\
            def test_noop():
                pass
        """)
    )

    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert "API Coverage Summary" not in result.stdout.str()


def test_plugin_multi_spec_with_config(pytester):
    """Plugin handles --coverage-config with multiple specs."""
    spec_a = pytester.makefile(
        ".yaml",
        spec_a=textwrap.dedent("""\
            openapi: "3.0.0"
            info:
              title: Service A
              version: "1.0"
            paths:
              /users:
                get:
                  responses:
                    "200":
                      description: OK
        """),
    )

    config_file = pytester.makefile(
        ".yaml",
        coverage_config=textwrap.dedent(f"""\
            specs:
              - name: svc-a
                api_filters:
                  - https://svc-a.example.com
                swagger_path: {spec_a}
        """),
    )

    pytester.makepyfile(
        textwrap.dedent("""\
            def test_noop():
                pass
        """)
    )

    result = pytester.runpytest(f"--coverage-config={config_file}")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*API Coverage Summary*"])


def test_spec_name_with_config_filters_spec(pytester):
    """--coverage-spec-name with --coverage-config selects only the named spec."""
    spec_a = pytester.makefile(
        ".yaml",
        spec_a=textwrap.dedent("""\
            openapi: "3.0.0"
            info:
              title: Service A
              version: "1.0"
            paths:
              /users:
                get:
                  responses:
                    "200":
                      description: OK
        """),
    )
    spec_b = pytester.makefile(
        ".yaml",
        spec_b=textwrap.dedent("""\
            openapi: "3.0.0"
            info:
              title: Service B
              version: "1.0"
            paths:
              /orders:
                get:
                  responses:
                    "200":
                      description: OK
        """),
    )

    config_file = pytester.makefile(
        ".yaml",
        coverage_config=textwrap.dedent(f"""\
            specs:
              - name: svc-a
                api_filters:
                  - https://svc-a.example.com
                swagger_path: {spec_a}
              - name: svc-b
                api_filters:
                  - https://svc-b.example.com
                swagger_path: {spec_b}
        """),
    )

    pytester.makepyfile(
        textwrap.dedent("""\
            def test_noop():
                pass
        """)
    )

    result = pytester.runpytest(
        f"--coverage-config={config_file}",
        "--coverage-spec-name=svc-a",
    )
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*API Coverage Summary*"])
    # Only svc-a should appear in the output
    assert "svc-a" in result.stdout.str()
    assert "svc-b" not in result.stdout.str()
