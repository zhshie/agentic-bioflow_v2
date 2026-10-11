// Fixture pipeline for the 008 run receiver tests: always succeeds, needs no
// container and no network. Three processes, six tasks.
process GREET {
    input:
    val x

    output:
    stdout

    script:
    """
    echo "hello ${x}"
    """
}

process UPPER {
    input:
    val s

    output:
    stdout

    script:
    """
    echo "${s.trim()}" | tr a-z A-Z
    """
}

process SUMMARY {
    input:
    val all

    output:
    stdout

    script:
    """
    echo "done ${all.size()}"
    """
}

workflow {
    greeted = GREET(Channel.of(1, 2, 3))
    shouted = UPPER(greeted)
    SUMMARY(shouted.collect())
}
