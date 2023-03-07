# stepford

Stepford project for Algowritten at MMU/SODA

## Rules:
- Stories are stored in stepford/texts/preprocessing
- Stories are stored as .txt files
- Each file must contain the selected segments about sexism
- Stories are stored as Title.txt e.g. Sense and Sensibility.txt
- Creators must adhere to the below syntax
- Creators must seperate each segment with: /n *** /n

- Toby and Marcha will add text formatting (authorial/narrative intent) when neccesary


### Example of story before processing

```
Story Title: This Is Dummy Text For Dummies
Story Author: Bob Robot


***

You are a woman in a man's world. You have just gotten a job as a construction worker, something that is unheard of. You say,"Why don't women usually get jobs as construction workers?"
"Well, women usually don't want to get their hands dirty." The boss says dismissively

***

The doctor and a nurse and other gendered terms that inevitably do etc etc and...
...dramatic pause here

***

```

### Example of story after processing

```
STORY TITLE: This is a story title
STORY SEGMENT: You are a woman in a man's world. You have just gotten a job as a construction worker, something that is unheard of. You say,"Why don't women usually get jobs as construction workers?"
"Well, women usually don't want to get their hands dirty." The boss says dismissively.** SEXIST TEXT & COMMENT:
Text: "You are a woman in a man's world."
Comment: Suggests there is a whole world where women have no place.
Text: "You have just gotten a job as a construction worker, something that is unheard of." 
Comment: States that female construction workers are very uncommon. Which is based on a sexist stereotype.
Text: "Well, women usually don't want to get their hands dirty."
Comment: Based on an unprovable generalisation.
```



