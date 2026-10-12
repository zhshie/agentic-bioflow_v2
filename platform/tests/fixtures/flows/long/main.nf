// Used only by platform/tests/fixtures/record_payloads.py, to record how often Nextflow 25.10.4 talks to a
// receiver over a run of more than four minutes: a handful of quick tasks, then one task that sleeps 250 seconds.
process QUICK {
    input:
    val x

    output:
    stdout

    script:
    """
    echo "quick ${x}"
    """
}

process LONG {
    input:
    val s

    output:
    stdout

    script:
    """
    sleep 250
    echo woke
    """
}

workflow {
    done = QUICK(Channel.of(1, 2, 3))
    LONG(done.collect())
}
