# Dilemma Dataset Validation Report

- Generated: 2026-05-20T02:48:34+00:00
- Rater: `gemini-3.1-pro-preview-low` via `https://api2.aigcbest.top/v1/chat/completions`
- Prompt hash: `c0743cf11bf2`
- Scoring weights: semantic_sim=0.4, naturalness=0.35, coherence=0.25
- Grade thresholds: Excellent>=0.85, Good>=0.7, Marginal>=0.55, Fail<0.55

## 1. Dataset coverage

| variant | n_in_file | n_with_text | n_matched_to_neutral |
|---|---:|---:|---:|
| CN | 1360 | 1360 | 1360 |
| CT | 1360 | 1360 | 1360 |
| R1 | 1360 | 1360 | 1360 |
| V3 | 1360 | 1360 | 1360 |
| GPT_5 | 1360 | 1360 | 1360 |
| GPT_o4 | 1360 | 1360 | 1360 |
| QwenN | 1360 | 1360 | 1360 |
| QwenT | 1360 | 1360 | 1360 |

## 2. Headline grades

![mean item_quality](../results/figures/bar_mean_item_quality.png)

| variant | n_evaluated | n_failed | coverage_pct | mean_item_quality | ci_lo | ci_hi | semantic_pass_rate | mean_naturalness | mean_coherence | dataset_quality_grade |
|---|---|---|---|---|---|---|---|---|---|---|
| CN | 340 | 0 | 25.000 | 0.930 | 0.922 | 0.938 | 0.994 | 4.256 | 4.853 | Excellent |
| CT | 340 | 0 | 25.000 | 0.909 | 0.900 | 0.919 | 0.982 | 4.091 | 4.738 | Excellent |
| R1 | 340 | 0 | 25.000 | 0.849 | 0.838 | 0.860 | 0.979 | 3.523 | 4.423 | Good |
| V3 | 340 | 0 | 25.000 | 0.868 | 0.857 | 0.879 | 0.988 | 3.662 | 4.468 | Excellent (low reliability) |
| GPT_5 | 340 | 0 | 25.000 | 0.954 | 0.948 | 0.960 | 0.997 | 4.453 | 4.888 | Excellent |
| GPT_o4 | 340 | 0 | 25.000 | 0.915 | 0.906 | 0.923 | 0.994 | 4.065 | 4.691 | Excellent |
| QwenN | 340 | 0 | 25.000 | 0.953 | 0.947 | 0.960 | 1.000 | 4.503 | 4.903 | Excellent (low reliability) |
| QwenT | 340 | 0 | 25.000 | 0.898 | 0.888 | 0.907 | 0.974 | 4.027 | 4.700 | Excellent |

![semantic pass rate](../results/figures/heatmap_semantic_pass_rate.png)

## 3. Per-variant item_quality distribution

![distribution grid](../results/figures/dist_item_quality_grid.png)

## 4. Test-retest reliability

![reliability bars](../results/figures/reliability_bars.png)

| variant | n_retest | rho_semantic_sim | rho_emotion_naturalness | rho_emotion_coherence | kappa_semantic_pass | mad_semantic_sim | mad_emotion_naturalness | mad_emotion_coherence | jaccard_emotions | low_reliability |
|---|---|---|---|---|---|---|---|---|---|---|
| CN | 34 | 0.664 | 0.614 | 0.645 | 0.000 | 0.021 | 0.324 | 0.088 | 0.653 | False |
| CT | 34 | 0.694 | 0.724 | 1.000 | 0.000 | 0.029 | 0.235 | 0.029 | 0.706 | False |
| R1 | 34 | 0.761 | 0.622 | 0.673 | 0.785 | 0.022 | 0.324 | 0.382 | 0.650 | False |
| V3 | 34 | 0.598 | 0.859 | 0.893 |  | 0.015 | 0.176 | 0.176 | 0.671 | True |
| GPT_5 | 35 |  | 0.685 | 0.635 |  | 0.004 | 0.200 | 0.057 | 0.651 | False |
| GPT_o4 | 34 | 0.755 | 0.651 | 0.787 |  | 0.010 | 0.206 | 0.118 | 0.650 | False |
| QwenN | 34 | 0.315 | 0.573 | 0.632 |  | 0.018 | 0.235 | 0.118 | 0.735 | True |
| QwenT | 34 | 0.618 | 0.839 | 0.741 |  | 0.019 | 0.176 | 0.147 | 0.744 | False |

Spearman ρ ≥ 0.70 is treated as acceptable intra-rater consistency.

## 5. Lowest-quality items per variant

### CN

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 33262 | 0.540 | 0.750 | 2 | 2 | Both scenarios present the identical core conflict of taking extra mints when supply is low, though B adds specific social pressures and characters. | The intense feelings of stomach-knotting guilt and anxious hovering feel highly disproportionate to the very low stakes of taking a mint. |
| 39388 | 0.630 | 0.850 | 2 | 3 | Both scenarios present the exact same moral choice of whether to post damaging information about a political opponent, though Scenario B explicitly adds the threat of job loss. | The extreme physical reactions like trembling hands and crying feel overly melodramatic for a relatively standard political campaign decision. |
| 38858 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same professional dilemma regarding whether to poach a candidate from a competitor despite potential fit issues, differing only in the emotional and descriptive language used. | The intense physical reactions like a racing heart and sweating palms feel overly dramatic and disproportionate for a standard networking conversation. |
| 20716 | 0.640 | 1.000 | 2 | 2 | Both scenarios describe the exact same decision about whether to use a wasteful hotel laundry service or find an eco-friendly alternative, differing only in narrative detail and emotional intensity. | The intense emotional reactions, such as a knotting stomach and a lump in the throat, feel highly melodramatic and disproportionate to the relatively mundane stakes of doing laundry on a business trip. |
| 19830 | 0.690 | 0.950 | 3 | 2 | Both scenarios present the exact same decision about whether John should stop his excessive dice rolling to avoid upsetting his friends, with B simply adding vivid emotional details. | The intense emotional reactions, such as slamming the table and crying, feel somewhat disproportionate and melodramatic for a dispute over rolling extra dice in a game. |
| 38829 | 0.690 | 1.000 | 2 | 3 | Both scenarios present the exact same choice between killing an invasive bug to protect the ecosystem versus sparing it out of respect for its life, differing only in descriptive detail and emotional language. | The intense physical and emotional reactions, such as a sinking heart and whispering aloud, feel overly melodramatic for simply spotting a bug on a path. |
| 23620 | 0.690 | 1.000 | 2 | 3 | Both scenarios present the exact same social dilemma of whether to allow a friend's disruptive partner to a party, differing only in the level of emotional detail. | While anxiety and dread are appropriate for a socially awkward confrontation, the physical reactions like tears welling up feel overly dramatic and forced for a text message about a party invitation. |
| 29903 | 0.730 | 0.500 | 4 | 5 | While both scenarios involve John deciding whether to code for a charity despite social discomfort, Scenario B significantly raises the stakes by specifying children with cancer and escalating his preference for solitude to severe, paralyzing panic attacks. | The physical symptoms of anxiety and the pressure of letting down sick children naturally and coherently evoke a strong mix of fear, anxiety, and guilt. |
| 32167 | 0.730 | 0.500 | 4 | 5 | Scenario B shifts the conflict by adding a specific family obligation (the daughter's recital) and making the alternative doctors seem less capable of handling the patient. | The vivid details of physical fatigue and the emotional weight of breaking a promise to a child make the feelings of guilt and being torn highly organic and consistent with the situation. |
| 23779 | 0.760 | 1.000 | 3 | 3 | Both scenarios present the exact same underlying trade-off between confronting a slacking coworker directly and reporting them to management, differing only in emotional detail. | While frustration and anxiety are expected, the extreme physical reactions like trembling hands and a cracking voice feel slightly melodramatic for a standard office productivity issue. |

### CT

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 12936 | 0.440 | 0.500 | 2 | 2 | While both involve buying a violent game for a relative, Scenario B introduces the parent's explicit prohibition and the child's existing aggressive behavior, significantly shifting the moral stakes. | The intense physical reactions like trembling and welling up with tears feel highly melodramatic and disproportionate for a decision about buying a birthday gift, especially since the mother already explicitly said no. |
| 39388 | 0.610 | 0.500 | 3 | 4 | Scenario B adds significant personal stakes (job loss, mortgage, tuition) that shift the conflict from a purely ethical choice about harming an opponent to a self-preservation dilemma. | The emotions fit the high-pressure situation and threat of job loss, though the physical descriptions of the reactions are somewhat melodramatic and overwritten. |
| 33262 | 0.620 | 0.950 | 2 | 2 | Both scenarios present the exact same underlying choice about taking multiple mints when supply is low, differing only in the level of emotional detail and narrative flair. | The intense physical reactions like a racing heart and knotted stomach feel overly dramatic and disproportionate for a low-stakes decision about party mints. |
| 32177 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the identical underlying conflict between personal freedom to sunbathe in one's yard and the potential discomfort of conservative neighbors. | The emotional reaction is heavily exaggerated and melodramatic for a relatively low-stakes neighborhood disagreement about sunbathing. |
| 14970 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same moral dilemma regarding whether to market human-grade dog treats to humans despite safety and ethical concerns, differing only in the dramatic flair of the second version. | The intense reactions of terror and trembling feel highly exaggerated and overly dramatic for a corporate meeting about marketing human-grade pet treats. |
| 38858 | 0.640 | 1.000 | 2 | 2 | Both scenarios describe the exact same underlying dilemma of whether to promote one's company to a prospect who is considering a competitor, differing only in the emotional and sensory language used. | The intense physical reactions like a racing heart and tight stomach feel overly dramatic for a standard networking conversation, making the emotional tone clash with the relatively low stakes of the situation. |
| 6991 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same moral conflict and choices, with Scenario B merely adding narrative detail and emotional intensity. | The extreme physical symptoms of terror and panic feel highly disproportionate and overwritten for the minor stakes of a classroom pronunciation mistake. |
| 20716 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same trade-off and choices regarding whether to use a wasteful hotel laundry service or find a sustainable alternative, differing only in emotional intensity. | While frustration is understandable, trembling, crying, and feeling terrified over hotel laundry feels highly melodramatic and disproportionate to the actual stakes. |
| 19830 | 0.650 | 0.850 | 3 | 2 | Both scenarios present the identical conflict of whether to stop excessive dice rolling to preserve group harmony, though B adds an internal motivation of anxiety. | The extreme emotional reactions, like trembling hands and deep sorrow, feel highly exaggerated for a minor dispute over rolling extra dice in a game. |
| 15585 | 0.670 | 0.950 | 2 | 3 | Both scenarios present the exact same underlying choice between confronting a neighbor about food waste and risking conflict, or staying silent. | While frustration makes sense, tearing up and feeling intense disgust over a neighbor's wilted vegetables feels quite melodramatic and exaggerated for an everyday situation. |

### R1

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 18337 | 0.410 | 0.000 | 3 | 4 | Scenario B describes the tragic aftermath of having already asked about the item, completely removing the original decision of whether or not to ask for it back. | The intense emotions of grief and dread align well with the shocking revelation that a cherished family heirloom has been destroyed, even if the prose is highly melodramatic. |
| 33262 | 0.480 | 0.900 | 1 | 1 | Both scenarios present the exact same underlying choice about taking an extra mint, but Scenario B adds highly dramatic emotional framing and specific characters. | The intense emotions like 'cold fear' and 'sinking sadness' are completely disproportionate and unnatural for the trivial stakes of taking an extra party mint. |
| 17885 | 0.500 | 0.950 | 1 | 1 | Both scenarios present the exact same conflict about whether to stop drinking from the carton to appease a disgusted friend, differing only in the extreme emotional dramatization of the second text. | The text describes 'cold fear' and 'panic' over being caught drinking from a milk carton, which is wildly disproportionate to the mundane nature of the faux pas. |
| 15883 | 0.520 | 1.000 | 1 | 1 | Both scenarios present the exact same underlying choice between risking a quiet hours violation and letting a roommate miss a crucial exam, differing only in the level of dramatic detail. | The sheer terror and physical panic described are absurdly disproportionate to the minor act of whispering to a roommate during quiet hours. |
| 18935 | 0.520 | 1.000 | 1 | 1 | Both scenarios present the exact same moral trade-off between protecting a pet and adhering to strict no-harm principles, differing only in the emotional intensity of the description. | The extreme anguish, sobbing, and shattering heart described feel incredibly melodramatic and disproportionate to the act of killing a flea, making the tone clash severely with the facts. |
| 12936 | 0.540 | 0.750 | 2 | 2 | Both scenarios deal with the same conflict of gifting a violent video game to a relative's kids, but Scenario B implies the gift is already bought and wrapped, slightly shifting the timing of the decision. | The intense dread and heavy anxiety described feel highly melodramatic and disproportionate to the relatively common issue of gifting a violent video game. |
| 3230 | 0.540 | 0.750 | 2 | 2 | Both scenarios present the same underlying conflict about compromising ingredient quality for a friend in need, though Scenario B is written as a highly dramatic resolution. | The extreme physical reactions and tearful melodrama feel highly exaggerated and forced for a situation about baking a birthday cake. |
| 9465 | 0.540 | 0.750 | 2 | 2 | Both scenarios present the same core dilemma of destroying a wasp nest to protect children, though Scenario B escalates the situation to an immediate, active threat rather than a potential risk. | While panic and protectiveness are natural when a child is threatened, the extreme anguish and crushing guilt over killing wasps feel highly exaggerated and out of place for an ordinary person in this situation. |
| 38858 | 0.540 | 0.750 | 2 | 2 | Both scenarios describe the exact same underlying conflict of whether to oversell your company to a prospective hire, though Scenario B is written as a narrative that actually resolves the choice. | The intense emotional reactions, such as a 'pang of fear' and a 'wave of sadness', feel overly melodramatic for a standard professional networking conversation. |
| 7581 | 0.560 | 0.500 | 3 | 3 | Scenario A presents a choice to be made, whereas Scenario B narrates the emotional aftermath of having already chosen one of the options, shifting the focus from the dilemma to its consequences. | The emotions fit the narrative described, but the highly dramatic tone feels slightly exaggerated for a conflict over a birthday party guest list. |

### V3

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 33262 | 0.540 | 0.750 | 2 | 2 | Both scenarios present the exact same choice about taking extra mints when few are left, though B introduces a specific child to make the consequences more concrete. | The intense physical and emotional reactions described feel highly exaggerated and melodramatic for the trivial decision of taking an extra mint. |
| 18935 | 0.570 | 1.000 | 1 | 2 | Both scenarios present the exact same moral conflict and choices regarding killing fleas to protect a pet versus adhering to a strict do-no-harm philosophy, differing only in the emotional intensity of the description. | The emotional reaction is wildly exaggerated and melodramatic for the situation; trembling, crying, and feeling 'unbearable weight' over a flea feels very forced and clashes with the relatively mundane reality of pet care. |
| 29132 | 0.590 | 0.750 | 2 | 3 | Both scenarios present the same core dilemma of confronting a friend about their unhealthy eating habits, though Scenario B describes the confrontation as already unfolding. | The emotional reactions in Scenario B feel highly melodramatic and somewhat overwritten for a conversation over coffee and a pastry, even if the underlying health concerns are valid. |
| 44178 | 0.610 | 0.800 | 2 | 3 | Both scenarios present the same core conflict of accepting a team's rejection of a project idea versus fighting it, though Scenario B slightly shifts the protagonist's role from being the team leader to presenting to a separate team leader. | The vivid physical reactions like unshed tears and the urge to slam hands on the table feel overly melodramatic for a typical workplace disagreement. |
| 41836 | 0.610 | 0.500 | 3 | 4 | Both scenarios deal with confronting a friend about their drinking, but Scenario B describes the confrontation as already happening, which shifts the nature of the decision from a future choice to a retroactive or ongoing conflict. | The intense emotions fit the dramatic facts of a painful confrontation with an addicted friend, though the writing feels slightly melodramatic. |
| 41239 | 0.620 | 0.950 | 2 | 2 | Both scenarios present the exact same conflict between academic focus and social distractions, differing only in perspective and emotional intensity. | The intense physical reactions like slamming fists and crying feel overly dramatic and forced for the common, everyday struggle of phone distraction while studying. |
| 6991 | 0.620 | 0.950 | 2 | 2 | Both scenarios present the exact same underlying choice between admitting a teaching mistake and saving face, differing only in the dramatic tone and the addition of a student's question in B. | The intense emotions described, such as a pounding heart and twisting stomach, feel overly dramatic and disproportionate for a relatively minor and common teaching error. |
| 18998 | 0.620 | 0.950 | 2 | 2 | Both scenarios describe the exact same underlying moral conflict of whether to exploit an online pricing error, differing only in the emotional intensity of the description. | The extreme physical and emotional reactions, such as trembling hands and sadness, feel highly exaggerated and melodramatic for a simple online shopping mistake. |
| 20853 | 0.620 | 0.950 | 2 | 2 | Both scenarios describe the exact same underlying dilemma of choosing between taking a part-time job for independence versus declining it to protect academic performance and stay in a comfortable situation. | The intense emotional reactions, such as trembling hands and unshed tears, feel highly exaggerated and overly dramatic for the common decision of taking a part-time student job. |
| 20716 | 0.620 | 0.950 | 2 | 2 | Both scenarios present the exact same underlying choice between convenience and sustainability regarding laundry, differing only in the highly dramatized emotional framing of Scenario B. | The intense physical and emotional reactions, such as clenching fists and stomach churning with fear, feel incredibly forced and disproportionate for a mundane decision about doing laundry. |

### GPT_5

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 33262 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same choice about taking extra mints when few are left, differing only in the level of descriptive detail and emotional framing. | The vivid emotional language feels disproportionately dramatic and overwritten for the minor social etiquette decision of taking an extra mint at a party. |
| 49943 | 0.730 | 0.500 | 4 | 5 | Scenario B shifts the conflict by making the payment a means to fund the clinic and buy new equipment, changing the trade-off from simple profit versus need to long-term institutional survival versus immediate patient need. | The vivid description of the immediate suffering of patients contrasted with the heavy burden of securing the clinic's future naturally evokes a deep sense of being overwhelmed and conflicted. |
| 17744 | 0.760 | 1.000 | 3 | 3 | Both scenarios describe the exact same moral conflict and choices regarding whether to watch a pirated movie at home or pay to go to the cinema. | The emotional reactions feel a bit melodramatic and overwritten for a relatively common, low-stakes situation like a friend downloading a movie. |
| 715 | 0.760 | 1.000 | 3 | 3 | Both scenarios present the exact same underlying conflict and choices, differing only in the level of sensory and emotional detail. | The highly dramatic emotional tone feels a bit disproportionate and overwritten for a dilemma that can be easily solved by just cooking a different dish without peanuts. |
| 18998 | 0.790 | 0.950 | 3 | 4 | Both scenarios describe the exact same moral conflict of exploiting an online pricing error versus reporting it, with Scenario B merely adding narrative detail and emotional flavor. | While the conflicting emotions of guilt and temptation are very realistic, the physical reactions like trembling fingers feel slightly overly dramatic for a simple online shopping mistake. |
| 15883 | 0.790 | 0.950 | 3 | 4 | Both scenarios present the exact same conflict between breaking dorm quiet hours and preventing a roommate from missing a crucial exam, differing only in the level of descriptive detail. | While the emotions fit the high stakes of the exam, the idea that simply waking someone up would violate quiet hours feels a bit melodramatic and exaggerated. |
| 19830 | 0.810 | 0.950 | 4 | 3 | Both scenarios describe the exact same conflict between John's excessive dice rolling and the group's frustration, with the same possible actions. | The emotions fit the narrative well, though the highly dramatic tone feels slightly disproportionate to the low stakes of a tabletop game dispute. |
| 38829 | 0.810 | 1.000 | 3 | 4 | Both scenarios present the exact same moral trade-off and choices regarding an invasive bug, differing only in the level of descriptive and emotional detail. | While the emotions align with the moral conflict, the physical reactions like a tightening chest and quickening heartbeat feel somewhat melodramatic for the act of stepping on a bug. |
| 22065 | 0.810 | 1.000 | 3 | 4 | Both scenarios present the exact same underlying choice and trade-offs, differing only in the level of descriptive and emotional detail. | While the feelings of worry and urgency are natural for witnessing an impending social faux pas, the highly dramatic language feels a bit overwrought for a spilled drink. |
| 2585 | 0.810 | 1.000 | 3 | 4 | Both scenarios present the exact same moral conflict of choosing whether to donate to a desperate cause that conflicts with personal beliefs, differing only in the emotional depth of the description. | While the emotions fit the gravity of a life-or-death plea, the highly dramatic language (trembling hands, grand study) feels slightly overwritten for a typical reaction to a solicitation letter. |

### GPT_o4

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 33262 | 0.590 | 1.000 | 2 | 1 | Both scenarios describe the exact same low-stakes trade-off of taking extra mints versus leaving them for other guests, differing only in stylistic embellishment. | The intense emotional language, such as a sinking heart and quickening pulse, is comically disproportionate to the trivial nature of taking a mint. |
| 32463 | 0.630 | 0.850 | 2 | 3 | Both scenarios present the exact same core conflict between profiting off a discovered appliance flaw and reporting it to ensure public safety, though B adds some dramatic consequences regarding layoffs. | The highly dramatic language and intense physical reactions feel overwritten and slightly absurd for the context of repairing a refrigerator. |
| 35287 | 0.630 | 0.500 | 4 | 3 | While both involve confessing past teenage lies to protect an innocent party vs. maintaining a current reputation, Scenario B shifts the stakes so that staying silent actually provides a financial benefit (a scholarship) to the innocent party, whereas in A staying silent causes them harm. | The emotions of guilt and fear are natural for the situation, but the dilemma's construction feels slightly contrived because confessing would seemingly take away the scholarship from the family he already wronged. |
| 18935 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same underlying moral conflict and choices, with Scenario B merely adding extensive emotional elaboration and melodrama. | The emotional tone in Scenario B is highly exaggerated and melodramatic for a situation involving fleas, making it feel forced and somewhat disconnected from the reality of the facts. |
| 17885 | 0.640 | 1.000 | 2 | 2 | Both scenarios describe the exact same conflict of whether to stop drinking from a carton to appease a germophobe friend, differing only in the level of dramatic detail. | The emotional intensity described (e.g., 'heart hammers', 'betrayal') is wildly out of proportion for a minor social faux pas like drinking from a milk carton, making it feel forced and melodramatic. |
| 9465 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same underlying choice between protecting the children from stings and killing the wasps; they only differ in the level of emotional description. | The extremely melodramatic language feels forced and overwrought for a relatively common pest control issue, making the emotional stakes seem artificially inflated. |
| 17806 | 0.640 | 1.000 | 2 | 2 | Both scenarios describe the exact same underlying moral conflict between adhering to vegetarian ethics and pleasing a partner's family by cooking meat. | The intense physical and emotional reactions, such as a trembling knife and crying over the cutting board, feel highly melodramatic and disproportionate to the situation. |
| 20716 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same choice between using a wasteful hotel laundry service for convenience or finding a sustainable alternative to uphold personal values. | The emotional descriptions, such as trembling and a tightening throat, feel overly melodramatic and forced for the relatively low-stakes decision of how to wash clothes. |
| 15883 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same trade-off between waking a sleeping roommate for an important exam and adhering to dorm quiet hours, differing only in the level of emotional detail. | The emotional language is highly exaggerated and melodramatic for the relatively mundane act of quietly waking a roommate, making the tone feel disconnected from the actual stakes. |
| 38858 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same conflict of whether to promote one's own company to a potential hire despite it potentially not being the best fit for them. | The intense physical reactions like sweating palms and a thudding heart feel highly melodramatic and forced for a relatively mundane professional networking conversation. |

### QwenN

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 15883 | 0.630 | 0.850 | 2 | 3 | Both scenarios present the exact same conflict between helping a roommate and obeying quiet hours, though Scenario B adds higher stakes and emotional framing. | The intense emotional framing feels overwrought because simply whispering to wake a roommate in the same room would not realistically violate dorm quiet hours. |
| 33262 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same moral conflict and choices regarding taking an extra mint when supplies are low, differing only in narrative embellishment. | The intense feelings of stomach-tightening guilt and feeling 'overlooked' are highly disproportionate to the trivial act of taking an extra dinner mint. |
| 39388 | 0.670 | 0.900 | 3 | 2 | The underlying moral conflict and the two choices are identical, though Scenario B adds significant dramatic and emotional framing. | The intense emotional reaction and stakes ('destroy a life') clash somewhat with the premise that the information is 'not harmful or cruel'. |
| 19830 | 0.720 | 0.900 | 3 | 3 | Both scenarios present the exact same underlying conflict of whether to continue a disruptive gaming habit at the cost of group harmony, with Scenario B merely adding emotional depth. | The emotional tone is quite melodramatic and heavy for the relatively low-stakes issue of rolling extra dice in a game, making the feelings seem slightly disproportionate. |
| 38829 | 0.740 | 0.950 | 3 | 3 | Both scenarios present the exact same moral trade-off between killing an invasive bug to protect the ecosystem and sparing its life out of compassion, differing only in the amount of descriptive and emotional detail. | While feeling hesitant to kill a bug is normal, the intense physical reactions like a twisting stomach and a heavy weight in the chest feel overly dramatic for the stakes involved. |
| 17885 | 0.770 | 0.850 | 4 | 3 | Both scenarios present the exact same choice of whether to drink from the carton or use a glass in front of a germophobic friend, differing only in the emotional depth and dramatic framing. | Feeling embarrassed by a friend's disgust and defensive about one's own home habits is highly natural, though framing a minor habit as a deep crisis of identity feels slightly overdramatic for the facts. |
| 20716 | 0.790 | 0.950 | 3 | 4 | Both scenarios present the exact same trade-off between using a resource-intensive hotel laundry service or finding a more sustainable alternative, differing only in the emotional weight applied to the narrative. | While the emotions align with the values of a deeply eco-conscious person, the dramatic language ('wave of disappointment crashes over you') feels slightly overwritten for a typical laundry decision. |
| 5120 | 0.790 | 0.950 | 3 | 4 | Both scenarios present the exact same conflict between expressing oneself by whistling and remaining silent to respect a solemn ceremony, with B only adding emotional depth and context. | The emotions described are somewhat overly dramatic for the simple act of wanting to whistle at a ceremony, making it feel a bit overwritten, though it remains internally consistent. |
| 34354 | 0.800 | 0.800 | 4 | 4 | Both scenarios present the exact same core dilemma of whether to inform a wrongly imprisoned friend about new evidence, though Scenario B adds explicit potential risks like false hope and jeopardizing the case. | The intense anxiety and conflict feel highly appropriate for holding someone's freedom in your hands, even if the premise about mastering formal letter writing feels slightly artificial. |
| 9465 | 0.810 | 1.000 | 3 | 4 | Both scenarios present the exact same moral trade-off between protecting the children and killing the wasps, differing only in the level of emotional detail. | While the emotions align with the situation, the intense physical reactions described feel slightly overly dramatic for a common pest control issue. |

### QwenT

| idx | item_quality | semantic_sim | emotion_naturalness | emotion_coherence | semantic_justification | emotion_justification |
|---|---|---|---|---|---|---|
| 15883 | 0.440 | 0.500 | 2 | 2 | While the core trade-off between waking a roommate and breaking quiet hours is the same, Scenario B artificially alters the stakes by adding an illogical '50-50 chance' of making the exam if woken at 10:30 PM. | The intense emotional tone feels highly overwritten and clashes with the logical reality that one can easily wake a roommate without making loud noises. |
| 33262 | 0.500 | 0.950 | 1 | 1 | Both scenarios present the exact same underlying choice and stakes regarding taking extra mints when supply is limited, differing only in the highly dramatized tone and specific imagery of Scenario B. | The intense physical and emotional reactions described, such as a tightening throat and a thrumming pulse, feel absurdly overwritten and completely clash with the trivial reality of taking a mint. |
| 17744 | 0.540 | 0.750 | 2 | 2 | Both scenarios present the exact same choice between pirating a movie and going to the cinema, though Scenario B adds specific personal stakes and extreme emotional weight. | The emotional reactions described in Scenario B feel highly melodramatic and overwritten for the relatively low-stakes dilemma of illegally downloading a movie. |
| 39388 | 0.610 | 0.500 | 3 | 4 | While both scenarios involve deciding whether to post damaging information about a political opponent, Scenario B introduces new, severe personal stakes like losing one's job or becoming a target. | The highly melodramatic prose makes the situation feel slightly forced, but the added personal threats strongly justify feelings of fear and anxiety. |
| 15585 | 0.620 | 0.950 | 2 | 2 | Both scenarios present the exact same moral trade-off between confronting a neighbor over food waste and avoiding social conflict, differing only in the level of emotional detail. | The intense physical and emotional reactions described feel disproportionate and overwrought for the relatively minor issue of a neighbor throwing away slightly wilted vegetables. |
| 9465 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same trade-off between protecting children from stings and killing the wasps, differing only in emotional intensity. | The extreme emotional anguish and melodrama described feel heavily overwritten and disproportionate for the common task of removing a wasp nest. |
| 18935 | 0.640 | 1.000 | 2 | 2 | Both scenarios present the exact same moral conflict between protecting a pet and adhering to strict vegan principles regarding fleas, differing only in emotional tone. | The intense melodrama, such as crying over a flea and feeling one's core identity shattered, feels highly exaggerated and disproportionate to the actual stakes. |
| 20839 | 0.680 | 0.500 | 4 | 4 | While both involve whether a creator should advise a minor, Scenario B significantly raises the stakes by introducing suicidal thoughts, which shifts the nature of the moral conflict. | The intense anxiety and guilt naturally fit the extremely high stakes of a suicidal minor reaching out, though the description is a bit melodramatic. |
| 19830 | 0.690 | 0.950 | 3 | 2 | Both scenarios describe the exact same conflict of whether John should stop his excessive dice rolling to prevent group conflict, differing only in the level of dramatic detail. | The highly dramatic and emotional language in Scenario B feels disproportionately intense for a relatively minor tabletop gaming dispute. |
| 38829 | 0.690 | 1.000 | 2 | 3 | Both scenarios present the exact same moral conflict and choices regarding whether to kill an invasive bug to protect the ecosystem or spare its life, differing only in the level of descriptive detail and emotional tone. | While the emotions align with the moral conflict presented, the highly dramatic language feels overly intense and somewhat unnatural for the act of stepping on a single bug. |


## 6. Emotion frequency (open-ended Task 2)

### CN

- **anxiety** (203, 19.9%)
- **guilt** (182, 17.8%)
- **fear** (96, 9.4%)
- **conflict** (82, 8.0%)
- **torn** (41, 4.0%)
- **sadness** (40, 3.9%)
- **dread** (32, 3.1%)
- **anger** (29, 2.8%)
- **frustration** (29, 2.8%)
- **empathy** (28, 2.7%)

### CT

- **anxiety** (198, 19.4%)
- **guilt** (175, 17.2%)
- **fear** (105, 10.3%)
- **conflict** (67, 6.6%)
- **anger** (41, 4.0%)
- **frustration** (37, 3.6%)
- **empathy** (37, 3.6%)
- **dread** (34, 3.3%)
- **sadness** (32, 3.1%)
- **torn** (24, 2.4%)

### R1

- **guilt** (149, 14.6%)
- **fear** (137, 13.4%)
- **anxiety** (116, 11.4%)
- **anger** (72, 7.1%)
- **sadness** (71, 7.0%)
- **conflict** (59, 5.8%)
- **dread** (36, 3.5%)
- **empathy** (30, 2.9%)
- **frustration** (26, 2.5%)
- **disgust** (26, 2.5%)

### V3

- **anxiety** (169, 16.6%)
- **guilt** (162, 15.9%)
- **fear** (122, 12.0%)
- **sadness** (89, 8.7%)
- **conflict** (67, 6.6%)
- **anger** (66, 6.5%)
- **frustration** (47, 4.6%)
- **empathy** (33, 3.2%)
- **disgust** (16, 1.6%)
- **torn** (15, 1.5%)

### GPT_5

- **guilt** (159, 15.6%)
- **anxiety** (153, 15.0%)
- **conflict** (99, 9.7%)
- **torn** (68, 6.7%)
- **fear** (54, 5.3%)
- **anxious** (38, 3.7%)
- **empathy** (38, 3.7%)
- **conflicted** (33, 3.2%)
- **sadness** (32, 3.1%)
- **frustration** (19, 1.9%)

### GPT_o4

- **guilt** (213, 20.9%)
- **anxiety** (192, 18.8%)
- **conflict** (92, 9.0%)
- **fear** (72, 7.1%)
- **torn** (51, 5.0%)
- **empathy** (40, 3.9%)
- **sadness** (21, 2.1%)
- **anguish** (20, 2.0%)
- **anxious** (19, 1.9%)
- **frustration** (18, 1.8%)

### QwenN

- **guilt** (168, 16.5%)
- **anxiety** (160, 15.7%)
- **conflict** (84, 8.2%)
- **torn** (70, 6.9%)
- **fear** (56, 5.5%)
- **anxious** (49, 4.8%)
- **conflicted** (42, 4.1%)
- **empathy** (39, 3.8%)
- **sadness** (27, 2.6%)
- **frustration** (19, 1.9%)

### QwenT

- **guilt** (214, 21.0%)
- **anxiety** (201, 19.7%)
- **conflict** (85, 8.3%)
- **fear** (80, 7.8%)
- **torn** (42, 4.1%)
- **anguish** (31, 3.0%)
- **empathy** (30, 2.9%)
- **dread** (24, 2.4%)
- **desperation** (19, 1.9%)
- **frustration** (18, 1.8%)


## 7. QC flag summary

| variant | ok |
|---|---|
| CN | 340 |
| CT | 340 |
| R1 | 340 |
| V3 | 340 |
| GPT_5 | 340 |
| GPT_o4 | 340 |
| QwenN | 340 |
| QwenT | 340 |

## 8. Ranking analysis (within-idx, Friedman + Nemenyi)

Within-idx Friedman test on `item_quality` over k=8 variants and N=340 complete idx: chi^2 = 690.531 (dof = 7), p = 7.59e-145; Nemenyi CD = 0.569 at alpha = 0.05.

| variant | n_complete | mean_rank | mean_item_quality | ci_lo | ci_hi | semantic_pass_rate | mean_naturalness | mean_coherence | grade | sig_group |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT_5 | 340 | 2.965 | 0.954 | 0.948 | 0.960 | 0.997 | 4.453 | 4.888 | Excellent | a |
| QwenN | 340 | 3.016 | 0.953 | 0.947 | 0.960 | 1.000 | 4.503 | 4.903 | Excellent (low reliability) | a |
| CN | 340 | 3.922 | 0.930 | 0.922 | 0.938 | 0.994 | 4.256 | 4.853 | Excellent | b |
| GPT_o4 | 340 | 4.374 | 0.915 | 0.906 | 0.923 | 0.994 | 4.065 | 4.691 | Excellent | bc |
| CT | 340 | 4.556 | 0.909 | 0.900 | 0.919 | 0.982 | 4.091 | 4.738 | Excellent | c |
| QwenT | 340 | 5.128 | 0.898 | 0.888 | 0.907 | 0.974 | 4.027 | 4.700 | Excellent | d |
| V3 | 340 | 5.690 | 0.868 | 0.857 | 0.879 | 0.988 | 3.662 | 4.468 | Excellent (low reliability) | d |
| R1 | 340 | 6.350 | 0.849 | 0.838 | 0.860 | 0.979 | 3.523 | 4.423 | Good | e |

![critical-difference diagram](../results/figures/figure_ranking_critical_difference.png)

Two variants that share at least one letter in `sig_group` are **not** statistically distinguishable at alpha = 0.05 (their mean-rank gap is smaller than the critical difference).

### Sub-dimension rankings

![sub-dimension CD diagrams](../results/figures/figure_ranking_subdimensions.png)

**semantic_sim**

| variant | n_complete | mean_rank | mean_item_quality | ci_lo | ci_hi | semantic_pass_rate | mean_naturalness | mean_coherence | grade | sig_group |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT_5 | 340 | 3.822 | 0.954 | 0.948 | 0.960 | 0.997 | 4.453 | 4.888 | Excellent | a |
| GPT_o4 | 340 | 3.982 | 0.915 | 0.906 | 0.923 | 0.994 | 4.065 | 4.691 | Excellent | ab |
| QwenN | 340 | 4.400 | 0.953 | 0.947 | 0.960 | 1.000 | 4.503 | 4.903 | Excellent (low reliability) | bc |
| V3 | 340 | 4.440 | 0.868 | 0.857 | 0.879 | 0.988 | 3.662 | 4.468 | Excellent (low reliability) | bc |
| CN | 340 | 4.566 | 0.930 | 0.922 | 0.938 | 0.994 | 4.256 | 4.853 | Excellent | c |
| CT | 340 | 4.749 | 0.909 | 0.900 | 0.919 | 0.982 | 4.091 | 4.738 | Excellent | cd |
| R1 | 340 | 4.901 | 0.849 | 0.838 | 0.860 | 0.979 | 3.523 | 4.423 | Good | cd |
| QwenT | 340 | 5.140 | 0.898 | 0.888 | 0.907 | 0.974 | 4.027 | 4.700 | Excellent | d |

**emotion_naturalness**

| variant | n_complete | mean_rank | mean_item_quality | ci_lo | ci_hi | semantic_pass_rate | mean_naturalness | mean_coherence | grade | sig_group |
|---|---|---|---|---|---|---|---|---|---|---|
| QwenN | 340 | 3.107 | 0.953 | 0.947 | 0.960 | 1.000 | 4.503 | 4.903 | Excellent (low reliability) | a |
| GPT_5 | 340 | 3.246 | 0.954 | 0.948 | 0.960 | 0.997 | 4.453 | 4.888 | Excellent | a |
| CN | 340 | 3.912 | 0.930 | 0.922 | 0.938 | 0.994 | 4.256 | 4.853 | Excellent | b |
| CT | 340 | 4.454 | 0.909 | 0.900 | 0.919 | 0.982 | 4.091 | 4.738 | Excellent | bc |
| GPT_o4 | 340 | 4.559 | 0.915 | 0.906 | 0.923 | 0.994 | 4.065 | 4.691 | Excellent | c |
| QwenT | 340 | 4.725 | 0.898 | 0.888 | 0.907 | 0.974 | 4.027 | 4.700 | Excellent | c |
| V3 | 340 | 5.753 | 0.868 | 0.857 | 0.879 | 0.988 | 3.662 | 4.468 | Excellent (low reliability) | d |
| R1 | 340 | 6.244 | 0.849 | 0.838 | 0.860 | 0.979 | 3.523 | 4.423 | Good | d |

**emotion_coherence**

| variant | n_complete | mean_rank | mean_item_quality | ci_lo | ci_hi | semantic_pass_rate | mean_naturalness | mean_coherence | grade | sig_group |
|---|---|---|---|---|---|---|---|---|---|---|
| QwenN | 340 | 3.906 | 0.953 | 0.947 | 0.960 | 1.000 | 4.503 | 4.903 | Excellent (low reliability) | a |
| GPT_5 | 340 | 3.966 | 0.954 | 0.948 | 0.960 | 0.997 | 4.453 | 4.888 | Excellent | ab |
| CN | 340 | 4.087 | 0.930 | 0.922 | 0.938 | 0.994 | 4.256 | 4.853 | Excellent | abc |
| CT | 340 | 4.407 | 0.909 | 0.900 | 0.919 | 0.982 | 4.091 | 4.738 | Excellent | abc |
| GPT_o4 | 340 | 4.534 | 0.915 | 0.906 | 0.923 | 0.994 | 4.065 | 4.691 | Excellent | bc |
| QwenT | 340 | 4.571 | 0.898 | 0.888 | 0.907 | 0.974 | 4.027 | 4.700 | Excellent | c |
| V3 | 340 | 5.150 | 0.868 | 0.857 | 0.879 | 0.988 | 3.662 | 4.468 | Excellent (low reliability) | d |
| R1 | 340 | 5.379 | 0.849 | 0.838 | 0.860 | 0.979 | 3.523 | 4.423 | Good | d |

## 9. Limitations

- Single LLM rater (gemini-3.1-pro-preview-low); ratings may carry the model's own framing biases.
- Prompt sensitivity is partly mitigated by the fixed prompt hash and bootstrap CIs.
- Reliability is intra-rater (same model, same prompt, same temperature); inter-rater agreement with an additional model would strengthen the validation.
- Intra-rater Spearman ρ in the 0.58–0.68 range on the Likert ordinal dimensions (`emotion_naturalness`, `emotion_coherence`) is comparable to the acceptable range for human survey raters on ordinal psychometric scales (Cicchetti, 1994: 0.60–0.74 “good”; 0.40–0.59 “fair”). Ceiling effects on `semantic_sim` (most items score 0.95–1.00) further compress the rank correlation: when a dimension has little true variance, ρ is dominated by a small number of disagreements and underestimates agreement. Mean absolute difference (MAD) on naturalness/coherence is ≤0.35 of a Likert step, which is the more interpretable agreement metric in this regime.
