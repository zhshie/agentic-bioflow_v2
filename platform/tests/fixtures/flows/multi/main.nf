// Fixture pipeline for the 007b launch tests: three processes and 13 tasks, each task sleeping a moment, so a
// run shows different numbers when it is looked at several times. No container, no network.
params.n = 8

process PREP {
    input:
    val x

    output:
    stdout

    script:
    """
    sleep 1
    echo "prep ${x}"
    """
}

process WORK {
    input:
    val x

    output:
    stdout

    script:
    """
    sleep 2
    echo "work ${x}"
    """
}

process MERGE {
    input:
    val all

    output:
    stdout

    script:
    """
    echo "merged ${all.size()}"
    """
}

workflow {
    PREP(Channel.of(1, 2, 3, 4))
    done = WORK(Channel.of(1..params.n))
    MERGE(done.collect())
}
