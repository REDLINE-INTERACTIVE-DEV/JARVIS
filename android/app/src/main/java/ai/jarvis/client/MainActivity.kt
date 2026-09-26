package ai.jarvis.client
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.concurrent.thread
class MainActivity:ComponentActivity(),TextToSpeech.OnInitListener{
 private var tts:TextToSpeech?=null
 override fun onCreate(b:Bundle?){super.onCreate(b);tts=TextToSpeech(this,this);setContent{App()}}
 override fun onInit(s:Int){if(s==TextToSpeech.SUCCESS)tts?.language=Locale.getDefault()}
 private fun speak(x:String){tts?.speak(x,TextToSpeech.QUEUE_FLUSH,null,"jarvis")}
 @Composable fun App(){var input by remember{mutableStateOf("")};val msgs=remember{mutableStateListOf<String>()}
  fun send(){val m=input.trim();if(m.isEmpty())return;input="";msgs.add("You: "+m);thread{try{val c=URL("http://10.0.2.2:8000/chat").openConnection() as HttpURLConnection;c.requestMethod="POST";c.doOutput=true;c.setRequestProperty("Content-Type","application/json");c.outputStream.use{it.write(("{\\"message\\":\\""+m.replace("\\","\\\\").replace("\"","\\\\\"")+"\\"}").toByteArray())};val raw=c.inputStream.bufferedReader().readText();val ans=raw.substringAfter("\"response\":\"").substringBeforeLast("\"");runOnUiThread{msgs.add("JARVIS: "+ans);speak(ans)}}catch(e:Exception){runOnUiThread{msgs.add("JARVIS: API error")}}}}
  fun voice(){if(!SpeechRecognizer.isRecognitionAvailable(this))return;val sr=SpeechRecognizer.createSpeechRecognizer(this);val i=Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);sr.setRecognitionListener(object:android.speech.RecognitionListener{override fun onResults(b:Bundle){input=b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty();sr.destroy();send()};override fun onError(e:Int){sr.destroy()};override fun onReadyForSpeech(p:Bundle?){};override fun onBeginningOfSpeech(){};override fun onRmsChanged(r:Float){};override fun onBufferReceived(b:ByteArray?){};override fun onEndOfSpeech(){};override fun onPartialResults(b:Bundle?){};override fun onEvent(t:Int,b:Bundle?){} });sr.startListening(i)}
  MaterialTheme{Column(Modifier.fillMaxSize().padding(16.dp)){Text("JARVIS",style=MaterialTheme.typography.headlineMedium);LazyColumn(Modifier.weight(1f)){items(msgs){Text(it,Modifier.padding(6.dp))}};Row{TextField(input,{input=it},Modifier.weight(1f));Button(onClick={voice()}){Text("Voice")};Button(onClick={send}){Text("Send")}}}}
 }
}