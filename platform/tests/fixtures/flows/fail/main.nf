// Fixture pipeline for the 008 run receiver tests: two tasks succeed, then one
// task exits 1 after printing a unique string to stderr. No container, no network.
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

process BAD {
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
    BAD(ok.collect())
}
