The dataset has:
1. Been reduced to fewer labels for easy early training. Reduced from a rough 13 labels down to 8 labels.
2. Empty rows removed
3. The CSV encoded to UTF-8 format. This is necessary for data integrity: 
                                                       a.)  **Universal Character Support**: UTF-8 can represent nearly all characters from every language, preventing issues with special characters,  
                                                       from every language, preventing issues with special characters, accents, or non-Latin scripts.
                                                       b.)  **Avoid Decoding Errors**: prevents UnicodeDecodeError by ensuring the file's encoding matches what your program expects
                                                       c.)  **Consistency in Tokenization**: Uniform UTF-8 encoding ensures that your text data is consistently interpreted, which is crucial for
                                                       accurate tokenization. 
                                                       d.) **Data Integrity**:  It preserves the original characters and symbols in your text data.
4. About ~1150 prompts with Max length: 14
                                                Median length: 4.0
                                                90th percentile length: 7.0
5. Currently two problematic label classes: Class 5: 'irrelevant'
                                                                    While its recall improved significantly, its precision was still modest, meaning other classes were sometimes misclassified as
                                                                    irrelevant.
                                                                    Class 6: 'notify_sos'
                                                                    This was the primary concern, as its recall significantly dropped. This means your model was missing a notable percentage of actual
                                                                    notify_sos requests, often misclassifying them as irrelevant or deny_taken. This is critical for a safety-focused intent.

Looking to get this dataset's current issues fixed and then add more labels and increase the total size to about 3k prompts.
