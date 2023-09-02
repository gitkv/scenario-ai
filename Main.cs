using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;
using System.Globalization;
using System.Linq;

public class AudioScriptManager : MonoBehaviour
{
    public AudioSource audioSource;
    public TMP_Text textObject;
    public TMP_Text scenarioNumberText;
    public GameObject coverImage;
    public string serverURL = "http://localhost:5000";
    public string standByText = "*работу работают*";
    public AudioClip laterClip;
    private bool waitingForClipToEnd = false;
    private int currentScenarioNumber = 1;
    private bool isFetchingData = false;
    private float retryDelay = 30f;
    private bool scenariosExist = false;
    private GameObject[] characters;
    private Coroutine idleCoroutine;

    [System.Serializable]
    public class Scenarios
    {
        public int[] scenarios;
    }

    void Start()
    {
        characters = GameObject.FindGameObjectsWithTag("Character");
        ClearOldFiles();
        InitializeAudio();
        StartCoroutine(GetDataFromServer());
    }

    void Update()
    {
        HandleAudioClip();
    }

    void InitializeAudio()
    {
        audioSource.playOnAwake = false;
        audioSource.loop = false;
        audioSource.Stop();
        audioSource.clip = null;
    }

    void HandleAudioClip()
    {
        if (!waitingForClipToEnd && !audioSource.isPlaying && audioSource.clip != null && !isFetchingData)
        {
            audioSource.clip = null;
            StartCoroutine(GetDataFromServer());
        }
    }

    void ClearOldFiles()
    {
        try
        {
            string scriptFilePath = "Assets/script.txt";
            string scenariosFilePath = "Assets/scenarios.json";
            
            if (File.Exists(scriptFilePath))
            {
                File.Delete(scriptFilePath);
                Debug.Log("Deleted old script.txt");
            }
            
            if (File.Exists(scenariosFilePath))
            {
                File.Delete(scenariosFilePath);
                Debug.Log("Deleted old scenarios.json");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error clearing old files: {e.Message}");
        }
    }

    IEnumerator GetDataFromServer()
    {
        isFetchingData = true;

        while (true)
        {
            yield return GetAvailableScenarios();

            if (scenariosExist)
            {
                StopIdleMode();
                yield return GetAudioClip();
                yield return GetScript();
                PlayAudioClip();
                waitingForClipToEnd = true;
                yield return ProcessScript();
                waitingForClipToEnd = false;
                StartCoroutine(DeleteScenario());
                yield return new WaitForSeconds(1.0f);
            }
            else
            {
                textObject.text = standByText;
                scenarioNumberText.text = "";
                StartIdleMode();
                yield return new WaitForSeconds(retryDelay);
            }
        }
    }

    IEnumerator GetAvailableScenarios()
    {
        using (UnityWebRequest www = UnityWebRequest.Get($"{serverURL}/scenarios"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError)
            {
                Debug.LogError(www.error);
                scenariosExist = false;
            }
            else
            {
                string scenariosFilePath = "Assets/scenarios.json";
                string jsonContent = "{\"scenarios\":" + www.downloadHandler.text + "}";
                File.WriteAllText(scenariosFilePath, jsonContent);

                Scenarios availableScenarios = JsonUtility.FromJson<Scenarios>(jsonContent);
                if (availableScenarios.scenarios.Length > 0)
                {
                    currentScenarioNumber = availableScenarios.scenarios.Min();
                    scenarioNumberText.text = "Серия: " + currentScenarioNumber;
                    scenariosExist = true;
                }
                else
                {
                    scenariosExist = false;
                }
            }
        }
    }

    IEnumerator GetAudioClip()
    {
        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip($"{serverURL}/audio/{currentScenarioNumber}", AudioType.MPEG))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError || www.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError(www.error);
                scenariosExist = false;
            }
            else
            {
                AudioClip audioClip = DownloadHandlerAudioClip.GetContent(www);
                audioSource.clip = audioClip;
            }
        }
    }

    IEnumerator GetScript()
    {
        using (UnityWebRequest www = UnityWebRequest.Get($"{serverURL}/script/{currentScenarioNumber}"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError)
            {
                Debug.LogError(www.error);
            }
            else
            {
                string script = www.downloadHandler.text;
                File.WriteAllText("Assets/script.txt", script);
            }
        }
    }

    void PlayAudioClip()
    {
        audioSource.Play();
    }

    IEnumerator ProcessScript()
    {
        string[] scriptLines = File.ReadAllLines("Assets/script.txt");

        foreach (string line in scriptLines)
        {
            textObject.text = null;
            (string speaker, string text, float duration) = ParseScriptLine(line);
            if (speaker == null || text == null || duration <= 0)
            {
                continue;
            }

            GameObject speakerObject = GameObject.Find(speaker);
            if (speakerObject == null)
            {
                continue;
            }

            Vector3 lookAtPosition = speakerObject.transform.position;
            lookAtPosition.y += 1.0f;

            textObject.text = text;
            yield return StartCoroutine(HandleScriptLine(lookAtPosition, duration));
        }

        yield return new WaitForSeconds(2.0f);
        yield return StartCoroutine(DisplayCoverAndWait(5.0f));
        PrepareScene();
        yield return new WaitForSeconds(1.0f);
    }

    IEnumerator HandleScriptLine(Vector3 lookAtPosition, float duration)
    {
        yield return StartCoroutine(CameraTransition(lookAtPosition, Camera.main.transform.rotation, 2.0f, 1.0f));
        yield return new WaitForSeconds(duration - 1.0f);
    }

    void PrepareScene()
    {
        textObject.text = "";
    }

    IEnumerator DisplayCoverAndWait(float seconds)
    {
        coverImage.SetActive(true);
        
        audioSource.clip = laterClip;
        audioSource.Play();
        yield return new WaitForSeconds(seconds);
        audioSource.Stop();
        coverImage.SetActive(false);
    }

    (string speaker, string text, float duration) ParseScriptLine(string line)
    {
        string[] parts = line.Split("::");
        if (parts.Length < 3)
        {
            return (null, null, -1);
        }

        string speaker = parts[0].Trim();
        string text = parts[1].Trim();
        if (float.TryParse(parts[2].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out float duration))
        {
            return (speaker, text, duration);
        }
        return (null, null, -1);
    }

    IEnumerator CameraTransition(Vector3 lookAtPosition, Quaternion startRotation, float targetSize, float transitionTime)
    {
        Quaternion targetRotation = Quaternion.LookRotation(lookAtPosition - Camera.main.transform.position);
        float elapsedTime = 0;

        while (elapsedTime < transitionTime)
        {
            elapsedTime += Time.deltaTime;
            float t = elapsedTime / transitionTime;

            Camera.main.transform.rotation = Quaternion.Slerp(startRotation, targetRotation, t);
            Camera.main.orthographicSize = Mathf.Lerp(Camera.main.orthographicSize, targetSize, t);

            yield return null;
        }
    }

    void StartIdleMode()
    {
        if (idleCoroutine == null)
        {
            idleCoroutine = StartCoroutine(IdleCameraBehavior());
        }
    }

    void StopIdleMode()
    {
        if (idleCoroutine != null)
        {
            StopCoroutine(idleCoroutine);
            idleCoroutine = null;
        }
    }

    IEnumerator IdleCameraBehavior()
    {
        while (true)
        {
            if (characters != null && characters.Length > 0)
            {
                int randomIndex = UnityEngine.Random.Range(0, characters.Length);
                GameObject targetCharacter = characters[randomIndex];

                Vector3 lookAtPosition = targetCharacter.transform.position;
                lookAtPosition.y += 1.0f;

                yield return CameraTransition(lookAtPosition, Camera.main.transform.rotation, 2.0f, 1.0f);
            }
            yield return new WaitForSeconds(3.0f);
        }
    }

    IEnumerator DeleteScenario()
    {
        using (UnityWebRequest www = UnityWebRequest.Delete($"{serverURL}/delete/{currentScenarioNumber}"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError)
            {
                Debug.LogError($"Failed to delete scenario {currentScenarioNumber}: {www.error}");
            }
            else
            {
                Debug.Log($"Scenario {currentScenarioNumber} deleted successfully");
            }
        }
    }
}
