// Fixture pipeline for the 007b launch tests: one task that fails on its first attempt and succeeds on its
// second (retried once), one task that always fails and is not retried, and two tasks that succeed.
// The run ends as failed. No container, no network.
process GOOD {
    input:
    val x

    output:
    stdout

    script:
    """
    echo "good ${x}"
    """
}

process FLAKY {
    errorStrategy 'retry'
    maxRetries 1

    input:
    val x

    output:
    stdout

    script:
    """
    if [ ${task.attempt} -eq 1 ]; then
        echo "FIXTURE_FLAKY_9" >&2
        exit 3
    fi
    echo "flaky ok ${x}"
    """
}

process BAD {
    errorStrategy 'finish'

    input:
    val s

    output:
    stdout

    script:
    """
    echo "FIXTURE_BOOM_7" >&2
    exit 1
    """
}

workflow {
    ok = GOOD(Channel.of(1, 2))
    FLAKY(Channel.of(1))
    BAD(ok.collect())
}
