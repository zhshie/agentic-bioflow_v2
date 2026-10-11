// Fixture pipeline for the 008 run receiver tests: three quick tasks finish at
// once, then one task sleeps about 20 seconds, so a run can be queried half way.
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

process SLEEPY {
    input:
    val s

    output:
    stdout

    script:
    """
    sleep 20
    echo woke
    """
}

workflow {
    SLEEPY(Channel.of(1))
    QUICK(Channel.of(1, 2, 3))
}
