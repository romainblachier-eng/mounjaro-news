#!/usr/bin/env python3
"""Ajoute un champ `title_fr` dans le frontmatter de chaque article.
Pour les articles déjà en français, recopie simplement le titre.
"""
import re
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1] / "content" / "posts"

# Mapping titre original -> titre FR. Si le titre est déjà en français on laisse identique.
TR = {
    "\"C'est dramatique\" : ce médicament pris par des millions de personnes fait grossir dès qu'on l'arrête - Journal des Femmes Santé":
        "\"C'est dramatique\" : ce médicament pris par des millions de personnes fait grossir dès qu'on l'arrête - Journal des Femmes Santé",
    "Interview exclusive — Dr Myriam Rosilio (Lilly France) : « Tirzépatide, des résultats inédits sur le cœur »":
        "Interview exclusive — Dr Myriam Rosilio (Lilly France) : « Tirzépatide, des résultats inédits sur le cœur »",
    "Médicament anti-obésité : la Haute autorité de santé donne son feu vert au remboursement de Mounjaro - Le Figaro Santé":
        "Médicament anti-obésité : la Haute Autorité de santé donne son feu vert au remboursement de Mounjaro - Le Figaro Santé",
    "Mounjaro Eye Side Effects Lawsuit [2026 Update]":
        "Effets secondaires oculaires du Mounjaro : le point sur les actions en justice [mise à jour 2026]",
    "Mounjaro : la HAS révise à la hausse l’amélioration du service médical rendu dans l’obésité":
        "Mounjaro : la HAS révise à la hausse l’amélioration du service médical rendu dans l’obésité",
    "MOUNJARO : nouveau médicament injectable indiqué dans le traitement du diabète de type 2 et de l'obésité":
        "MOUNJARO : nouveau médicament injectable indiqué dans le traitement du diabète de type 2 et de l'obésité",
    "Mounjaro: Why medical experts say Kenyans should be cautious - Daily Nation":
        "Mounjaro : pourquoi les experts médicaux appellent les Kényans à la prudence - Daily Nation",
    "Note d’Allurion Technologies relevée suite à l’approbation de la FDA - Investing.com France":
        "Note d’Allurion Technologies relevée suite à l’approbation de la FDA - Investing.com France",
    "Obésité : remboursement de Mounjaro":
        "Obésité : remboursement de Mounjaro",
    "Que se passe-t-il lorsqu'on arrête les GLP-1 ?":
        "Que se passe-t-il lorsqu'on arrête les GLP-1 ?",
    "Wegovy vs. Mounjaro: 8 Important Differences":
        "Wegovy vs Mounjaro : 8 différences importantes",
    "Allurion Announces Partnership to Offer Combination Therapy with Mounjaro® (tirzepatide) at Discounted Prices - Yahoo Finance":
        "Allurion annonce un partenariat pour proposer une thérapie combinée avec Mounjaro® (tirzépatide) à prix réduit - Yahoo Finance",
    "Eli Lilly’s weight loss and diabetes drug tops Keytruda as world’s best-selling medicine":
        "Le médicament anti-obésité et antidiabète d’Eli Lilly dépasse Keytruda comme médicament le plus vendu au monde",
    "Weight-Loss Drug Linked to Lower Risk of Eye Disease in Patients with Diabetes - WCM Newsroom":
        "Un médicament anti-obésité associé à un moindre risque de maladie oculaire chez les patients diabétiques - WCM Newsroom",
    "Mounjaro health benefits found to reverse one year after stopping drug - The Pharmaceutical Journal":
        "Les bénéfices du Mounjaro s’inversent un an après l’arrêt du traitement - The Pharmaceutical Journal",
    "Tirzepatide as Compared with Semaglutide for the Treatment of Obesity | New England Journal of Medicine - The New England Journal of Medicine":
        "Tirzépatide versus sémaglutide dans le traitement de l’obésité - New England Journal of Medicine",
    "Vital Signs: Pharma's fastest growing drugs":
        "Signes vitaux : les médicaments qui progressent le plus vite dans la pharma",
    "Clean Eatz Kitchen Launches Subscription-Free GLP-1 Meal Plan for Ozempic®, Wegovy®, and Mounjaro® Users - PR Newswire":
        "Clean Eatz Kitchen lance un plan repas GLP-1 sans abonnement pour les utilisateurs d’Ozempic®, Wegovy® et Mounjaro® - PR Newswire",
    "Keytruda Hangs On to Best Seller Crown as GLP-1s Gain Ground":
        "Keytruda conserve sa couronne de meilleure vente, mais les GLP-1 gagnent du terrain",
    "La FDA américaine met en garde 30 sociétés de télésanté contre des publicités trompeuses pour des médicaments":
        "La FDA américaine met en garde 30 sociétés de télésanté contre des publicités trompeuses pour des médicaments",
    "Drugmaker Aspen targets Mounjaro approval in sub-Saharan Africa this year":
        "Le laboratoire Aspen vise l’approbation du Mounjaro en Afrique subsaharienne cette année",
    "Ozempic-like weight loss drugs may help the heart recover after a heart attack":
        "Les médicaments type Ozempic pourraient aider le cœur à récupérer après un infarctus",
    "What will change in Canada when generic Ozempic hits the market, according to our reporters - The Globe and Mail":
        "Ce qui va changer au Canada avec l’arrivée de l’Ozempic générique, selon nos journalistes - The Globe and Mail",
    "Augmentation des ventes de médicaments contre l'obésité au Portugal - The Portugal News":
        "Augmentation des ventes de médicaments contre l'obésité au Portugal - The Portugal News",
    "New analysis of GLP-1 drugs suggests people who stopped using medications regained 60% of weight lost - ABC News":
        "Une nouvelle analyse sur les GLP-1 indique que les personnes ayant arrêté le traitement ont repris 60 % du poids perdu - ABC News",
    "Quitting Mounjaro and Wegovy jabs might actually leave you worse off than before":
        "Arrêter les injections de Mounjaro et Wegovy pourrait vous laisser dans un état pire qu’avant",
    "Eli Lilly continue à prendre de l'embonpoint, sur un marché de plus en plus concurrentiel - Les Echos":
        "Eli Lilly continue à prendre de l'embonpoint, sur un marché de plus en plus concurrentiel - Les Echos",
    "Ozempic, Wegovy & Similar Drugs: What the Lawsuits Are About - The National Law Review":
        "Ozempic, Wegovy et médicaments similaires : ce que révèlent les actions en justice - The National Law Review",
    "La nouvelle génération des médicaments contre l'obésité - QUB radio":
        "La nouvelle génération des médicaments contre l'obésité - QUB radio",
    "WEGOVY, SAXENDA, MOUNJARO : prescription élargie à tout médecin, y compris en initiation de traitement":
        "WEGOVY, SAXENDA, MOUNJARO : prescription élargie à tout médecin, y compris en initiation de traitement",
    "What Are GLP-1s? Uses for Weight Loss, Diabetes, and More":
        "Les GLP-1, c’est quoi ? Usages dans la perte de poids, le diabète et au-delà",
    "Eli Lilly Employer Connect Launch Puts Obesity Drug Push And Rich Valuation Under The Microscope":
        "Le lancement d’Eli Lilly Employer Connect place la stratégie obésité et la valorisation du groupe sous les projecteurs",
    "GLP-1 drugs like Ozempic can raise bone and tendon injury risk, study suggests - The Detroit News":
        "Les GLP-1 comme l’Ozempic pourraient accroître le risque de blessures osseuses et tendineuses, selon une étude - The Detroit News",
    "Two deaths reported to drug watchdog over potential link to weight-loss jabs":
        "Deux décès signalés aux autorités sanitaires en lien possible avec des injections minceur",
    "Lilly rewards CEO David Ricks with $36.7M pay package for 2025, fueled by GLP-1 success - Fierce Pharma":
        "Lilly octroie à son PDG David Ricks une rémunération de 36,7 M$ pour 2025, portée par le succès des GLP-1 - Fierce Pharma",
    "Médicaments anti-obésité : la prescription élargie à tous les médecins en France":
        "Médicaments anti-obésité : la prescription élargie à tous les médecins en France",
    "Mounjaro Cleared for Type 2 Diabetes in EU Children":
        "Mounjaro autorisé chez l’enfant atteint de diabète de type 2 dans l’UE",
    "Wegovy users have five times greater risk of sudden sight loss than Ozempic users, study finds - The Guardian":
        "Les utilisateurs de Wegovy auraient un risque de perte soudaine de la vue cinq fois supérieur à ceux sous Ozempic, selon une étude - The Guardian",
    "Which GLP-1 drug has the highest risk of sudden sight loss and ‘eye stroke’: study - New York Post":
        "Quel GLP-1 présente le plus haut risque de perte soudaine de la vue et d’« AVC oculaire » : les résultats d’une étude - New York Post",
    "Ce médicament prescrit contre l’obésité fait perdre jusqu’à 20 % de son poids initial, mais son arrêt inquiète la médecine car il entraîne une reprise rapide des kilos et un impact immédiat sur la santé cardiovasculaire - Science et vie":
        "Ce médicament prescrit contre l’obésité fait perdre jusqu’à 20 % de son poids initial, mais son arrêt inquiète la médecine car il entraîne une reprise rapide des kilos et un impact immédiat sur la santé cardiovasculaire - Science et vie",
    "Lilly finds impurity in compounded version of its weight-loss drug, warns of health risks":
        "Lilly détecte une impureté dans une version composée de son médicament anti-obésité et alerte sur des risques sanitaires",
    "Mounjaro, Wegovy - La prescription des traitements de l’obésité est étendue - Actualité - Que Choisir":
        "Mounjaro, Wegovy - La prescription des traitements de l’obésité est étendue - Actualité - Que Choisir",
    "An open letter from Eli Lilly and Company warning of potential patient safety risks associated with tirzepatide compounded with vitamin B12 - Eli Lilly":
        "Lettre ouverte d’Eli Lilly alertant sur des risques potentiels pour la sécurité des patients liés au tirzépatide composé avec de la vitamine B12 - Eli Lilly",
    "Impurity in Some Compounded Tirzepatide 'Potentially Dangerous,' Eli Lilly Warns - MedPage Today":
        "Une impureté « potentiellement dangereuse » dans certaines versions composées du tirzépatide, alerte Eli Lilly - MedPage Today",
    "Lilly warns of impurity in compounded versions of tirzepatide - FirstWord Pharma":
        "Lilly alerte sur une impureté dans des versions composées du tirzépatide - FirstWord Pharma",
    "Eli Lilly finds impurity in compounded tirzepatide - Pharmaceutical Technology":
        "Eli Lilly détecte une impureté dans le tirzépatide composé - Pharmaceutical Technology",
    "In latest compounding clash, Lilly flags high levels of 'impurity' in tirzepatide knockoffs with vitamin B12 - Fierce Pharma":
        "Nouveau bras de fer sur les préparations magistrales : Lilly signale des taux élevés d’« impuretés » dans des copies de tirzépatide avec vitamine B12 - Fierce Pharma",
    "Lilly Says Compounded Tirzepatide With Added Vitamin B12 Contains Impurities. Is It Safe? - Everyday Health":
        "Selon Lilly, le tirzépatide composé avec de la vitamine B12 contient des impuretés. Est-ce sûr ? - Everyday Health",
    "Compounded version of Eli Lilly GLP-1 may have impurity, company warns":
        "Une version composée du GLP-1 d’Eli Lilly pourrait contenir une impureté, prévient le laboratoire",
    "Lilly découvre une impureté dans une version composée de son médicament pour la perte de poids et met en garde":
        "Lilly découvre une impureté dans une version composée de son médicament pour la perte de poids et met en garde",
    "Why compounded Mounjaro may be riskier than you think, especially if it contains B12 - The South First":
        "Pourquoi le Mounjaro composé peut être plus risqué qu’on ne le pense, surtout s’il contient de la B12 - The South First",
    "What Happens When Patients Stop Taking GLP-1 Drugs? New Cleveland Clinic Study Reveals Real World Insights - Cleveland Clinic Newsroom":
        "Que se passe-t-il quand les patients arrêtent les GLP-1 ? Une nouvelle étude de la Cleveland Clinic livre des données de vie réelle - Cleveland Clinic Newsroom",
    "Un médicament contre l’obésité permet de perdre jusqu’à 20 % du poids, mais son arrêt inquiète les médecins - Science et vie":
        "Un médicament contre l’obésité permet de perdre jusqu’à 20 % du poids, mais son arrêt inquiète les médecins - Science et vie",
    "Semaglutide vs. Tirzepatide for Weight Loss - US News Health":
        "Sémaglutide vs tirzépatide pour la perte de poids - US News Health",
    "Stopping GLP-1 drugs can quickly erase cardiovascular benefits - Medical Xpress":
        "Arrêter les GLP-1 peut effacer rapidement les bénéfices cardiovasculaires - Medical Xpress",
    "Why Did Eli Lilly Stock Slide 6% Despite Strong GLP-1 Momentum?":
        "Pourquoi l’action Eli Lilly a-t-elle chuté de 6 % malgré une forte dynamique des GLP-1 ?",
    "Lilly’s triple G agonist succeeds in Phase III diabetes trial - Clinical Trials Arena":
        "L’agoniste triple G de Lilly réussit son essai de phase III dans le diabète - Clinical Trials Arena",
    "Stopping GLP-1 drugs can quickly erase cardiovascular benefits - WashU Medicine":
        "Arrêter les GLP-1 peut rapidement effacer les bénéfices cardiovasculaires - WashU Medicine",
    "What happens after Ozempic shocked researchers":
        "Ce qui se passe après l’arrêt d’Ozempic a surpris les chercheurs",
    "Early use of tirzepatide after heart attack or stroke linked to key cardiovascular benefits - Cardiovascular Business":
        "Administrer tôt le tirzépatide après un infarctus ou un AVC apporte des bénéfices cardiovasculaires majeurs - Cardiovascular Business",
    "GLP-1 Vision Loss Lawsuits: Ozempic, Wegovy, and NAION Optic Nerve Injury Claims - JD Supra":
        "Actions en justice GLP-1 et perte de vision : Ozempic, Wegovy et les plaintes pour NAION - JD Supra",
    "Heart Benefits From GLP-1 Drugs Fade After Stopping, Study Finds - U.S. News & World Report":
        "Les bénéfices cardiaques des GLP-1 s’estompent après l’arrêt, selon une étude - U.S. News & World Report",
    "Generic semaglutide in India, and other weight-loss news":
        "Sémaglutide générique en Inde et autres actualités de la perte de poids",
    "Mounjaro : le traitement minceur qui augmente la poitrine ? Effets secondaires et explications":
        "Mounjaro : le traitement minceur qui augmente la poitrine ? Effets secondaires et explications",
    "Weight Loss Drugs in India: Ozempic and Wegovy Alternatives, Explained - Open Magazine":
        "Médicaments de perte de poids en Inde : les alternatives à Ozempic et Wegovy expliquées - Open Magazine",
    "Beyond the weight-loss injection: How this 44-year-old balances Mounjaro with diet, exercise and sleep - The Indian Express":
        "Au-delà de l’injection minceur : comment cette femme de 44 ans combine Mounjaro, alimentation, exercice et sommeil - The Indian Express",
    "Eli Lilly and Company (LLY) Expands Zepbound Access as Pricing Reforms Boost Long-Term Growth Outlook - Yahoo! Finance Canada":
        "Eli Lilly (LLY) élargit l’accès à Zepbound alors que les réformes tarifaires renforcent ses perspectives de croissance - Yahoo! Finance Canada",
    "India's drug regulator tightens surveillance against unauthorized weight-loss drug sales":
        "Le régulateur indien durcit la surveillance contre les ventes non autorisées de médicaments minceur",
    "Stopping GLP-1 Drugs May Raise Heart Risks":
        "Arrêter les GLP-1 pourrait augmenter les risques cardiaques",
    "Ce duo de traitement a permis à 120 femmes de perdre 35 % de poids en plus à la ménopause - Top Santé":
        "Ce duo de traitement a permis à 120 femmes de perdre 35 % de poids en plus à la ménopause - Top Santé",
    "Improved Heart and Kidney Outcomes for Type 1 Diabetes Patients Taking GLP-1 Weight Loss Drugs - Johns Hopkins Bloomberg School of Public Health":
        "Meilleure santé cardiaque et rénale chez les patients atteints de diabète de type 1 sous GLP-1 - Johns Hopkins Bloomberg School of Public Health",
    "Weight-gain fears after stopping Ozempic unfounded – Cleveland Clinic study - Medical Brief":
        "La crainte d’une reprise de poids après l’arrêt d’Ozempic serait infondée, selon la Cleveland Clinic - Medical Brief",
    "Orforglipron vs. Tirzepatide: Weight Loss Pill vs. Injection":
        "Orforglipron vs tirzépatide : la pilule minceur face à l’injection",
    "Traitement de l’obésité La chirurgie fait mieux que les médicaments tels que Wegovy et Mounjaro - UFC-Que Choisir":
        "Traitement de l’obésité : la chirurgie fait mieux que les médicaments tels que Wegovy et Mounjaro - UFC-Que Choisir",
    "Why tirzepatide is better than semaglutide, GLP-1 medication guide - USA Today":
        "Pourquoi le tirzépatide surpasse le sémaglutide : guide des médicaments GLP-1 - USA Today",
    "13 surprising ways GLP-1s may benefit the body, according to science - The Washington Post":
        "13 bénéfices surprenants des GLP-1 pour l’organisme, selon la science - The Washington Post",
    "GLP-1 agonists could be a global game-changer, but need to be accessible and affordable":
        "Les agonistes GLP-1 pourraient tout changer à l’échelle mondiale, à condition d’être accessibles et abordables",
    "Opinion | Taking Ozempic (or other GLP-1 drugs) isn’t cheating":
        "Tribune | Prendre de l’Ozempic (ou un autre GLP-1) n’est pas tricher",
    "Tirzepatide Associated with Lower Risk of Heart and Kidney Damage Compared to Dulaglutide in Patients with Type 2 Diabetes and Cardiovascular Disease - Cleveland Clinic Newsroom":
        "Le tirzépatide associé à un moindre risque d’atteintes cardiaques et rénales que le dulaglutide chez les patients diabétiques de type 2 atteints de maladie cardiovasculaire - Cleveland Clinic Newsroom",
    "Vanessa Williams Has Had A Striking Transformation Thanks To Mounjaro":
        "La transformation spectaculaire de Vanessa Williams grâce au Mounjaro",
    "Allurion Announces Partnership to Offer Combination Therapy with Mounjaro® (tirzepatide) at Discounted Prices - Business Wire":
        "Allurion annonce un partenariat pour proposer une thérapie combinée avec Mounjaro® (tirzépatide) à prix réduit - Business Wire",
    "Lilly's Mounjaro (tirzepatide), a GIP/GLP-1 dual receptor agonist, reduced A1C by an average of 2.2% in a Phase 3 trial of children and adolescents with type 2 diabetes - PR Newswire":
        "Le Mounjaro (tirzépatide) de Lilly, agoniste double des récepteurs GIP/GLP-1, réduit l’HbA1c de 2,2 % en moyenne dans un essai de phase 3 chez l’enfant et l’adolescent diabétiques de type 2 - PR Newswire",
    "Beyond Diabetes Control: Tirzepatide Boosts Quality of Life":
        "Au-delà du contrôle du diabète : le tirzépatide améliore la qualité de vie",
    "Cardiovascular Outcomes with Tirzepatide versus Dulaglutide in Type 2 Diabetes":
        "Résultats cardiovasculaires du tirzépatide versus dulaglutide dans le diabète de type 2",
    "A Second Weight Loss Pill Just Hit the Market. Here’s How It’s Different. - Men's Health":
        "Une deuxième pilule minceur arrive sur le marché : voici ce qui la distingue - Men’s Health",
    "FDA Approves Eli Lilly's Obesity Pill, Foundayo - Time Magazine":
        "La FDA approuve Foundayo, la pilule anti-obésité d’Eli Lilly - Time Magazine",
    "With an FDA nod, Lilly's oral GLP-1 enters the obesity ring as Foundayo - FirstWord Pharma":
        "Feu vert de la FDA : le GLP-1 oral de Lilly entre dans l’arène de l’obésité sous le nom Foundayo - FirstWord Pharma",
    "FDA approves Foundayo, Eli Lilly's new GLP-1 obesity pill - LiveNOW from FOX":
        "La FDA approuve Foundayo, la nouvelle pilule GLP-1 anti-obésité d’Eli Lilly - LiveNOW from FOX",
    "Tirzepatide Effective Despite Weight-Inducing Meds":
        "Le tirzépatide reste efficace malgré la prise de médicaments favorisant la prise de poids",
    "Joi + Blokes Compounded GLP-1 Review 2026: Semaglutide, Tirzepatide, Pricing, and Everything to Verify Before You Enroll":
        "Revue 2026 des GLP-1 composés Joi + Blokes : sémaglutide, tirzépatide, prix et tout ce qu’il faut vérifier avant de s’inscrire",
    "Lilly's Mounjaro (tirzepatide), a GIP/GLP-1 dual receptor agonist, reduced A1C by an average of 2.2% in a Phase 3 trial of children and adolescents with type 2 diabetes - Eli Lilly":
        "Le Mounjaro (tirzépatide) de Lilly, agoniste double des récepteurs GIP/GLP-1, réduit l’HbA1c de 2,2 % en moyenne dans un essai de phase 3 chez l’enfant et l’adolescent diabétiques de type 2 - Eli Lilly",
    "9 Foundayo (Orforglipron) Side Effects You Should Know About":
        "9 effets secondaires du Foundayo (orforglipron) à connaître",
    "Actualité - Analogues du GLP-1 indiqués dans le traitement de l’obésité : l’ANSM fait évoluer leurs conditions de prescription et de délivrance":
        "Actualité - Analogues du GLP-1 indiqués dans le traitement de l’obésité : l’ANSM fait évoluer leurs conditions de prescription et de délivrance",
    "Mounjaro slimming syringe - Reuters Connect":
        "Seringue minceur Mounjaro - Reuters Connect",
    "9 Mounjaro Alternatives for Weight Loss and Diabetes":
        "9 alternatives au Mounjaro pour la perte de poids et le diabète",
    "Can Mounjaro Make Birth Control Less Effective? - MedShadow Foundation":
        "Le Mounjaro peut-il réduire l’efficacité de la contraception ? - MedShadow Foundation",
    "Scientists Uncover New Metabolic Effects Beyond Weight Loss of Mounjaro":
        "Des scientifiques découvrent de nouveaux effets métaboliques du Mounjaro au-delà de la perte de poids",
    "Weight Loss After Tirzepatide Varies by Prior Weight Change":
        "La perte de poids sous tirzépatide varie selon les antécédents pondéraux",
    "If you aren’t losing weight with GLP-1 drugs, this may be one reason why - The Boston Globe":
        "Vous ne perdez pas de poids avec les GLP-1 ? Voici une explication possible - The Boston Globe",
    "Ozempic Weight Loss Success Varies by DNA - Neuroscience News":
        "La perte de poids sous Ozempic varie selon l’ADN - Neuroscience News",
    "Weight-loss drugs: Who benefits most and why?":
        "Médicaments de perte de poids : à qui profitent-ils le plus, et pourquoi ?",
    "Evidence, excitement: In the moment with a GLP-1 expert - UW Medicine | Newsroom":
        "Preuves et enthousiasme : entretien avec une experte des GLP-1 - UW Medicine | Newsroom",
    "Pharmacists Play Central Role in Optimizing Tirzepatide Use for Type 2 Diabetes - Pharmacy Times":
        "Les pharmaciens jouent un rôle central dans l’optimisation du tirzépatide pour le diabète de type 2 - Pharmacy Times",
    "Tirzepatide Outperforms Dulaglutide on Cardiorenal Outcomes in High-Risk Diabetes - The American Journal of Managed Care® (AJMC®)":
        "Le tirzépatide surpasse le dulaglutide sur les issues cardiorénales dans le diabète à haut risque - The American Journal of Managed Care® (AJMC®)",
    "GLP-1 weight loss, side effects linked to genetic variations":
        "Perte de poids et effets secondaires des GLP-1 liés à des variations génétiques",
    "Pharma 50: Keytruda holds the top brand slot, but tirzepatide and semaglutide have already passed it at the molecule level in FY2025":
        "Pharma 50 : Keytruda reste la marque n°1, mais tirzépatide et sémaglutide l’ont déjà dépassée au niveau de la molécule en 2025",
    "Unlocking the Genetics of GLP-1 Medications: Why Your DNA Matters - 23andMe Blog":
        "Décrypter la génétique des GLP-1 : pourquoi votre ADN compte - 23andMe Blog",
    "Health Rounds : Variations génétiques liées à la perte de poids et aux effets secondaires des médicaments GLP-":
        "Health Rounds : variations génétiques liées à la perte de poids et aux effets secondaires des médicaments GLP-1",
    "Mounjaro monthly sales drop for first time in March, semaglutide gains volume":
        "Les ventes mensuelles de Mounjaro reculent pour la première fois en mars, le sémaglutide gagne en volume",
    "Cheaper generics capture 20% of weight-loss mkt - The Times of India":
        "Les génériques moins chers captent 20 % du marché de la perte de poids - The Times of India",
    "Not losing weight on Mounjaro or Ozempic? Your genes could be the reason, says new study - The Indian Express":
        "Vous ne maigrissez pas sous Mounjaro ou Ozempic ? Vos gènes pourraient en être la cause, selon une nouvelle étude - The Indian Express",
    "Ozempic vs Mounjaro: What India’s first real-world study says, and why the timing matters - The South First":
        "Ozempic vs Mounjaro : ce que révèle la première étude indienne en vie réelle, et pourquoi le moment est crucial - The South First",
}


def escape_yaml(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    m = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not m:
        return False
    fm = m.group(1)

    if re.search(r'^title_fr:', fm, re.MULTILINE):
        return False  # already done

    tm = re.search(r'^title:\s*"(.+)"\s*$', fm, re.MULTILINE)
    if not tm:
        return False
    raw_title = tm.group(1)
    # unescape backslash-escaped quotes
    title = raw_title.replace('\\"', '"').replace('\\\\', '\\')

    fr = TR.get(title, title)
    fr_line = f'title_fr: "{escape_yaml(fr)}"'

    # Insert title_fr right after title line
    new_fm = re.sub(
        r'^(title:\s*".+"\s*)$',
        lambda mo: mo.group(1) + '\n' + fr_line,
        fm,
        count=1,
        flags=re.MULTILINE,
    )

    new_text = '---\n' + new_fm + '\n---\n' + text[m.end():]
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    count = 0
    missing = []
    for p in sorted(CONTENT.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
        if m:
            tm = re.search(r'^title:\s*"(.+)"\s*$', m.group(1), re.MULTILINE)
            if tm:
                title = tm.group(1).replace('\\"', '"').replace('\\\\', '\\')
                if title not in TR:
                    missing.append(title)
        if process_file(p):
            count += 1
    print(f"{count} fichiers mis à jour")
    if missing:
        print(f"⚠️  {len(missing)} titres non traduits :")
        for t in missing:
            print(f"   - {t}")


if __name__ == "__main__":
    main()
