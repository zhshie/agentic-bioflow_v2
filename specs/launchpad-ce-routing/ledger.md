# launchpad-ce-routing progress ledger

## RED (before implementation), tests/prepare_launch_ce_test.sh: 30 FAIL, 23 ok (TC-024 and the quiet/regression checks already green)
```
TC-001 bound to line names the CE                                       
TC-002 DECIDE names both CEs + --compute-env                            
TC-002 says do NOT launch by short name                                 
TC-005 bound to right after registered                                  
TC-025 json list has workspace                                          
TC-006 names CE                                                         
TC-006 matches wording                                                  
TC-008 view fallback names CE                                           
TC-008 view fallback DECIDE                                             
TC-025 view has -n and workspace                                        
TC-009 view fallback match                                              
TC-011 view top-level computeEnv                                        
TC-011 DECIDE                                                           
TC-010 launch.computeEnv read                                           
TC-010 DECIDE                                                           
TC-012 SEQERA_COMPUTE_ENV wins                                          
TC-014 wanted revision wrong -> DECIDE                                  
TC-015 wanted revision right -> match                                   
TC-016 no revision field -> DECIDE                                      
TC-017 unknown                                                          
TC-018 unknown                                                          
TC-019 exactly one bound-to warning                                     
TC-019 wording                                                          
TC-020 unknown on bad json                                              
TC-020 one warning                                                      
TC-021 no compute_env text                                              
TC-021 names CE                                                         
TC-022 fixed warning                                                    
TC-028 step 3 mentions bound to                                         
TC-029 step 7 explicit --compute-env                                    
30 FAIL
```

## GREEN
- scripts/prepare_launch.sh: `bound to:` line, DECIDE on mismatch, WARNING on unknown/unset (view fallback max 5).
- skills/launch/SKILL.md: step 3 skips only when registered + bound to matches; step 7 always passes `--compute-env`.
- docs/PITFALLS.md: item 55 appended (renumbered from 54 when merging v3, which added its own 54).
- tests/prepare_launch_ce_test.sh: all green.

## Manual steps (TC-030, 031, 032)
- TC-030/031: read steps 3 and 7 of skills/launch/SKILL.md; step 3 skips only on registered + matching bound to; step 7 says always pass --compute-env.
- TC-032 (UNVERIFIED, does not block merge): on a logged-in machine with tw 0.40, run `tw -o json pipelines list --workspace <id>` and `tw -o json pipelines view -n <name> --workspace <id>`, feed to prepare_launch.sh, confirm `bound to:` shows the real CE and note the field position here.
